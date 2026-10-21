import os
import threading
import sqlite3
import json
import time

import sys
import shutil

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_user_data_dir():
    """Returns the persistent User Data directory across OS updates and app reinstalls."""
    env_user_data = os.environ.get("EVERYTHING_USER_DATA")
    if env_user_data:
        try:
            os.makedirs(env_user_data, exist_ok=True)
            return env_user_data
        except Exception:
            pass

    if "VERCEL" in os.environ:
        p = "/tmp/MeikovaHarvest"
        os.makedirs(p, exist_ok=True)
        return p

    if sys.platform.startswith("win") and "APPDATA" in os.environ:
        p = os.path.join(os.environ["APPDATA"], "MeikovaHarvest")
        try:
            os.makedirs(p, exist_ok=True)
            return p
        except Exception:
            pass

    if sys.platform == "darwin":
        p = os.path.expanduser("~/Library/Application Support/MeikovaHarvest")
        try:
            os.makedirs(p, exist_ok=True)
            return p
        except Exception:
            pass

    if sys.platform.startswith("linux"):
        xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        p = os.path.join(xdg, "MeikovaHarvest")
        try:
            os.makedirs(p, exist_ok=True)
            return p
        except Exception:
            pass

    p = os.path.join(BASE_DIR, "data")
    try:
        os.makedirs(p, exist_ok=True)
        return p
    except Exception:
        import tempfile
        p = os.path.join(tempfile.gettempdir(), "MeikovaHarvest")
        os.makedirs(p, exist_ok=True)
        return p

def migrate_legacy_user_data(legacy_dir, target_user_dir):
    """Safely migrates legacy downloads.db, cookies, and bypass data to the persistent user data directory."""
    migrated = False
    if not os.path.exists(legacy_dir) or not os.path.exists(target_user_dir):
        return False
    
    if os.path.abspath(legacy_dir) == os.path.abspath(target_user_dir):
        return False

    legacy_db = os.path.join(legacy_dir, "downloads.db")
    target_db = os.path.join(target_user_dir, "downloads.db")
    if os.path.exists(legacy_db) and not os.path.exists(target_db):
        try:
            shutil.copy2(legacy_db, target_db)
            for ext in ["-wal", "-shm"]:
                wal_f = legacy_db + ext
                if os.path.exists(wal_f):
                    shutil.copy2(wal_f, target_db + ext)
            migrated = True
        except Exception as e:
            print(f"[Migration] Failed to copy legacy database: {e}")

    legacy_cookies = os.path.join(legacy_dir, "cookies")
    target_cookies = os.path.join(target_user_dir, "cookies")
    if os.path.isdir(legacy_cookies):
        os.makedirs(target_cookies, exist_ok=True)
        try:
            for item in os.listdir(legacy_cookies):
                src_f = os.path.join(legacy_cookies, item)
                dst_f = os.path.join(target_cookies, item)
                if os.path.isfile(src_f) and not os.path.exists(dst_f):
                    shutil.copy2(src_f, dst_f)
                    migrated = True
        except Exception as e:
            print(f"[Migration] Failed to copy legacy cookies: {e}")

    return migrated

# Persistent user data directory
USER_DATA_DIR = get_user_data_dir()
COOKIES_DIR = os.path.join(USER_DATA_DIR, "cookies")
os.makedirs(COOKIES_DIR, exist_ok=True)

# Path to SQLite database in persistent User Data directory
DB_PATH = os.path.join(USER_DATA_DIR, "downloads.db")

# Downloads directory for temporary staging
if "VERCEL" in os.environ:
    TEMP_DOWNLOAD_DIR = "/tmp/downloads"
else:
    TEMP_DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")

try:
    os.makedirs(TEMP_DOWNLOAD_DIR, exist_ok=True)
except OSError:
    import tempfile
    TEMP_DOWNLOAD_DIR = os.path.join(tempfile.gettempdir(), "MeikovaHarvest", "downloads")
    os.makedirs(TEMP_DOWNLOAD_DIR, exist_ok=True)

try:
    migrate_legacy_user_data(TEMP_DOWNLOAD_DIR, USER_DATA_DIR)
except Exception:
    pass

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
                    timestamp REAL,
                    user_id TEXT,
                    sync_status TEXT DEFAULT 'synced',
                    sync_time REAL DEFAULT 0
                )
            ''')
            try:
                cursor.execute("ALTER TABLE downloads ADD COLUMN user_id TEXT")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE downloads ADD COLUMN sync_status TEXT DEFAULT 'synced'")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE downloads ADD COLUMN sync_time REAL DEFAULT 0")
            except Exception:
                pass
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloads_user_id ON downloads(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloads_sync_status ON downloads(sync_status)")
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
                ("ophim.org", "ophim"),
                ("guphim.com", "guphim"),
                ("guphim.co", "guphim"),
                ("guphim.net", "guphim"),
                ("guphim.org", "guphim"),
                ("luphim.com", "luphim"),
                ("luphim.co", "luphim"),
                ("luphim.net", "luphim"),
                ("luphim.org", "luphim"),
                ("animevietsub.love", "animevietsub"),
                ("animevietsub.fan", "animevietsub"),
                ("animevietsub.lol", "animevietsub"),
                ("animevietsub.in", "animevietsub"),
                ("animevietsub.tv", "animevietsub"),
                ("animevietsub.site", "animevietsub"),
                ("animevietsub.id", "animevietsub"),
                ("animevietsub.pl", "animevietsub"),
                ("animevietsub.by", "animevietsub"),
                ("animevietsub.ru", "animevietsub"),
                ("animevietsub.my", "animevietsub")
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
                user_id = task_data.get("user_id")
                sync_status = task_data.get("sync_status", "pending_sync")
                cursor.execute(
                    "INSERT INTO downloads (download_id, data, timestamp, user_id, sync_status) VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(download_id) DO UPDATE SET data = ?, timestamp = ?, user_id = COALESCE(?, user_id), sync_status = ?",
                    (download_id, json.dumps(task_data), task_data.get("timestamp", time.time()), user_id, sync_status,
                     json.dumps(task_data), task_data.get("timestamp", time.time()), user_id, sync_status)
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

    def get_history(self, limit=50, user_id=None):
        history_list = []
        rows = []
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=5.0)
                conn.execute("PRAGMA journal_mode=WAL")
                cursor = conn.cursor()
                if user_id:
                    cursor.execute(
                        "SELECT download_id, data FROM downloads WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                        (user_id, limit)
                    )
                else:
                    cursor.execute("SELECT download_id, data FROM downloads ORDER BY timestamp DESC LIMIT ?", (limit,))
                rows = cursor.fetchall()
                conn.close()
            except Exception as e:
                print(f"Error fetching history: {e}")
                return []

        # Process outside of self.lock to avoid holding thread lock during disk I/O
        for download_id, data_str in rows:
            try:
                data = json.loads(data_str)
                data["download_id"] = download_id
                filepath = data.get("filepath")
                file_exists = False
                file_size = 0
                if filepath:
                    try:
                        if os.path.exists(filepath):
                            file_exists = True
                            file_size = os.path.getsize(filepath)
                    except Exception:
                        pass
                data["file_exists"] = file_exists
                data["file_size"] = file_size
                history_list.append(data)
            except Exception:
                pass
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

    def clear_history(self, user_id=None):
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=5.0)
                conn.execute("PRAGMA journal_mode=WAL")
                cursor = conn.cursor()
                if user_id:
                    cursor.execute("DELETE FROM downloads WHERE user_id = ?", (user_id,))
                else:
                    cursor.execute("DELETE FROM downloads")
                conn.commit()
                conn.close()
                if not user_id:
                    self.clear()
                return True
            except Exception as e:
                print(f"Error clearing history: {e}")
                return False

    def get_pending_sync(self, user_id=None):
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=5.0)
                conn.execute("PRAGMA journal_mode=WAL")
                cursor = conn.cursor()
                if user_id:
                    cursor.execute("SELECT download_id, data FROM downloads WHERE user_id = ? AND sync_status = 'pending_sync'", (user_id,))
                else:
                    cursor.execute("SELECT download_id, data FROM downloads WHERE sync_status = 'pending_sync'")
                rows = cursor.fetchall()
                conn.close()
                items = []
                for d_id, data_str in rows:
                    try:
                        d = json.loads(data_str)
                        d["download_id"] = d_id
                        items.append(d)
                    except Exception:
                        pass
                return items
            except Exception as e:
                print(f"Error fetching pending sync items: {e}")
                return []

    def mark_synced(self, download_ids):
        if not download_ids:
            return
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=5.0)
                conn.execute("PRAGMA journal_mode=WAL")
                cursor = conn.cursor()
                now = time.time()
                for d_id in download_ids:
                    cursor.execute("UPDATE downloads SET sync_status = 'synced', sync_time = ? WHERE download_id = ?", (now, d_id))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Error marking synced: {e}")

# Global persistent dictionary for tracking download tasks and lock for thread safety
downloads_status = PersistentDownloadStatus(DB_PATH)
downloads_status_lock = threading.Lock()

# Global AuthManager for user identity & session management
from utils.auth import AuthManager
auth_manager = AuthManager(DB_PATH)
