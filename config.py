import os
import threading
import sqlite3
import json
import time

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Downloads directory
TEMP_DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(TEMP_DOWNLOAD_DIR, exist_ok=True)

# Path to SQLite database
DB_PATH = os.path.join(TEMP_DOWNLOAD_DIR, "downloads.db")

class PersistentTaskDict(dict):
    def __init__(self, download_id, initial_data, db_save_callback):
        super().__init__(initial_data)
        self.download_id = download_id
        self.db_save_callback = db_save_callback

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.db_save_callback(self.download_id, dict(self))

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self.db_save_callback(self.download_id, dict(self))

class PersistentDownloadStatus(dict):
    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_db()
        self._load_active_and_cleanup()

    def _init_db(self):
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS downloads (
                    download_id TEXT PRIMARY KEY,
                    data TEXT,
                    timestamp REAL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bypass_domains (
                    domain TEXT PRIMARY KEY,
                    bypass_reason TEXT,
                    timestamp REAL
                )
            ''')
            # Pre-seed popular custom streaming domains
            pre_seeded = [
                ("motchilltv.lt", "motchill"),
                ("motchilltv.pm", "motchill"),
                ("motchilltv.to", "motchill"),
                ("motchilltv.co", "motchill"),
                ("motchill.co", "motchill"),
                ("motchill.org", "motchill"),
                ("ghienphim.co", "ghienphim"),
                ("ghienphim.org", "ghienphim"),
                ("ghienphim3.co", "ghienphim"),
                ("phimmoi.net", "phimmoi"),
                ("phimmoichill.net", "phimmoi"),
                ("phimmoichill.org", "phimmoi"),
                ("phimmoichill.co", "phimmoi"),
                ("phim1080.in", "phim1080"),
                ("phim1080.org", "phim1080"),
                ("phim1080.net", "phim1080"),
                ("bilutv.link", "bilutv"),
                ("bilutv.org", "bilutv"),
                ("bilutv.co", "bilutv"),
                ("dongphim.com", "dongphim"),
                ("dongphim.net", "dongphim"),
                ("dongphim.co", "dongphim"),
                ("ophim.co", "ophim"),
                ("ophim.cc", "ophim"),
                ("ophim.org", "ophim")
            ]
            for dom, reason in pre_seeded:
                cursor.execute(
                    "INSERT OR IGNORE INTO bypass_domains (domain, bypass_reason, timestamp) VALUES (?, ?, ?)",
                    (dom, reason, time.time())
                )
            conn.commit()
            conn.close()

    def _load_active_and_cleanup(self):
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()
            cursor.execute("SELECT download_id, data FROM downloads")
            rows = cursor.fetchall()
            for download_id, data_str in rows:
                try:
                    data = json.loads(data_str)
                    status = data.get("status")
                    if status in ["pending", "downloading", "merging", "processing"]:
                        # Server restarted, mark interrupted downloads as failed
                        data["status"] = "error"
                        data["message"] = "Server restarted. Task interrupted."
                        data["error"] = "Interrupted"
                        cursor.execute("UPDATE downloads SET data = ? WHERE download_id = ?", (json.dumps(data), download_id))
                except Exception:
                    pass
            conn.commit()
            conn.close()

    def _save_task(self, download_id, task_data):
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=10.0)
                conn.execute("PRAGMA journal_mode=WAL")
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO downloads (download_id, data, timestamp) VALUES (?, ?, ?) "
                    "ON CONFLICT(download_id) DO UPDATE SET data = ?, timestamp = ?",
                    (download_id, json.dumps(task_data), task_data.get("timestamp", time.time()), json.dumps(task_data), task_data.get("timestamp", time.time()))
                )
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Error saving to SQLite: {e}")

    def __setitem__(self, download_id, val):
        if not isinstance(val, PersistentTaskDict):
            val = PersistentTaskDict(download_id, val, self._save_task)
        super().__setitem__(download_id, val)
        self._save_task(download_id, dict(val))

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        for k, v in self.items():
            if not isinstance(v, PersistentTaskDict):
                self[k] = PersistentTaskDict(k, v, self._save_task)
            self._save_task(k, dict(v))

    def get(self, download_id, default=None):
        if download_id in self:
            return super().get(download_id, default)
        
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=5.0)
                conn.execute("PRAGMA journal_mode=WAL")
                cursor = conn.cursor()
                cursor.execute("SELECT data FROM downloads WHERE download_id = ?", (download_id,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    data = json.loads(row[0])
                    wrapped = PersistentTaskDict(download_id, data, self._save_task)
                    super().__setitem__(download_id, wrapped)
                    return wrapped
            except Exception:
                pass
        return default

    def pop(self, download_id, default=None):
        # We only delete it from in-memory dict so RAM doesn't grow,
        # but we DO NOT delete it from SQLite to keep it in the history.
        return super().pop(download_id, default)

    def get_history(self, limit=50):
        history_list = []
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=5.0)
                conn.execute("PRAGMA journal_mode=WAL")
                cursor = conn.cursor()
                cursor.execute("SELECT download_id, data FROM downloads ORDER BY timestamp DESC LIMIT ?", (limit,))
                rows = cursor.fetchall()
                conn.close()
                for download_id, data_str in rows:
                    try:
                        data = json.loads(data_str)
                        data["download_id"] = download_id
                        filepath = data.get("filepath")
                        data["file_exists"] = bool(filepath and os.path.exists(filepath))
                        history_list.append(data)
                    except Exception:
                        pass
            except Exception as e:
                print(f"Error fetching history: {e}")
        return history_list

    def delete_task(self, download_id):
        with self.lock:
            try:
                if download_id in self:
                    super().pop(download_id, None)
                conn = sqlite3.connect(self.db_path, timeout=5.0)
                conn.execute("PRAGMA journal_mode=WAL")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM downloads WHERE download_id = ?", (download_id,))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"Error deleting task {download_id}: {e}")
                return False

    def clear_history(self):
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=5.0)
                conn.execute("PRAGMA journal_mode=WAL")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM downloads")
                conn.commit()
                conn.close()
                self.clear()
                return True
            except Exception as e:
                print(f"Error clearing history: {e}")
                return False

# Global persistent dictionary for tracking download tasks and lock for thread safety
downloads_status = PersistentDownloadStatus(DB_PATH)
downloads_status_lock = threading.Lock()
