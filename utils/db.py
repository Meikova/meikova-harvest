# -*- coding: utf-8 -*-
"""
Meikova Harvest — Dual Database Adapter (SQLite WAL + Turso Cloud libSQL)
Supports:
- Turso Cloud SQLite over libSQL HTTP pipeline when TURSO_DATABASE_URL and TURSO_AUTH_TOKEN are set.
- Local SQLite with WAL mode, busy timeout 10.0s, and Row factory fallback.
"""

import os
import atexit
import sqlite3
import threading
from typing import Any, List, Optional, Tuple, Union


def load_dotenv(dotenv_path: Optional[str] = None) -> None:
    """Loads environment variables from .env file using standard library."""
    if dotenv_path is None:
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.isfile(dotenv_path):
        try:
            with open(dotenv_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = val
        except Exception:
            pass


load_dotenv()


def _patch_libsql_daemon():
    """Patches libsql_client sync executor to ensure background worker thread is a daemon."""
    try:
        import libsql_client.sync
        if getattr(libsql_client.sync, "_daemon_patched", False):
            return
        orig_init = libsql_client.sync._AsyncExecutor.__init__

        def _safe_init(self):
            import asyncio, collections
            self._thread = threading.Thread(target=self._run, name="libsql_client", daemon=True)
            self._loop = asyncio.new_event_loop()
            self._lock = threading.Lock()
            self._closed = False
            self._queue = collections.deque()
            self._waker = None
            self._thread.start()

        libsql_client.sync._AsyncExecutor.__init__ = _safe_init
        libsql_client.sync._daemon_patched = True
    except Exception:
        pass


class HarvestDbAdapter:
    def __init__(
        self,
        local_path: str,
        url: Optional[str] = None,
        auth_token: Optional[str] = None,
    ):
        self.local_path = str(local_path)
        raw_url = (url if url is not None else os.environ.get("TURSO_DATABASE_URL", "")).strip()
        # Convert libsql:// to https:// for Hrana / libSQL HTTP pipeline compatibility
        if raw_url.startswith("libsql://"):
            self.turso_url = "https://" + raw_url[len("libsql://"):]
        else:
            self.turso_url = raw_url

        self.turso_token = (auth_token if auth_token is not None else os.environ.get("TURSO_AUTH_TOKEN", "")).strip()
        self.is_turso = bool(self.turso_url and self.turso_token)
        self._turso_client = None
        self._lock = threading.RLock()
        atexit.register(self.close)

    def _get_turso_client(self):
        with self._lock:
            if self._turso_client is None or getattr(self._turso_client, "closed", False):
                _patch_libsql_daemon()
                import libsql_client
                self._turso_client = libsql_client.create_client_sync(
                    self.turso_url,
                    auth_token=self.turso_token
                )
            return self._turso_client

    def _execute_local(self, sql: str, params: tuple = ()):
        parent_dir = os.path.dirname(os.path.abspath(self.local_path))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        conn = sqlite3.connect(self.local_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()
            cursor.execute(sql, params)
            upper_sql = sql.strip().upper()
            if upper_sql.startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "REPLACE")):
                conn.commit()
            return cursor.fetchall()
        finally:
            conn.close()

    def execute(self, sql: str, params: Any = ()):
        """Executes a SQL statement and returns fetched rows (if any)."""
        args = list(params) if isinstance(params, (tuple, list)) else ([] if params is None else [params])
        if self.is_turso:
            try:
                client = self._get_turso_client()
                res = client.execute(sql, args)
                return res.rows
            except Exception as e:
                # Turso network/query error -> fallback to local SQLite
                with self._lock:
                    self._turso_client = None
                print(f"[Turso Harvest Error] {e}, falling back to local SQLite")

        return self._execute_local(sql, tuple(args))

    def fetchone(self, sql: str, params: Any = ()):
        rows = self.execute(sql, params)
        return rows[0] if rows else None

    def fetchall(self, sql: str, params: Any = ()):
        return self.execute(sql, params)

    def executemany(self, sql: str, seq_of_params: list):
        if not seq_of_params:
            return []

        if self.is_turso:
            try:
                _patch_libsql_daemon()
                import libsql_client
                client = self._get_turso_client()
                stmts = [
                    libsql_client.Statement(
                        sql,
                        list(p) if isinstance(p, (tuple, list)) else ([] if p is None else [p])
                    )
                    for p in seq_of_params
                ]
                res = client.batch(stmts)
                return [r.rows for r in res]
            except Exception as e:
                with self._lock:
                    self._turso_client = None
                print(f"[Turso Harvest Error] {e}, falling back to local SQLite")

        parent_dir = os.path.dirname(os.path.abspath(self.local_path))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        conn = sqlite3.connect(self.local_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()
            formatted = [tuple(p) if isinstance(p, (tuple, list)) else (p,) for p in seq_of_params]
            cursor.executemany(sql, formatted)
            conn.commit()
            return cursor.fetchall()
        finally:
            conn.close()

    def close(self):
        with self._lock:
            if self._turso_client is not None:
                try:
                    self._turso_client.close()
                except Exception:
                    pass
                self._turso_client = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
