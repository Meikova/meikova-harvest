import os
import sqlite3
import hashlib
import secrets
import uuid
import time
import json
import base64
import urllib.request
import urllib.error

# Universal SSO Interop
try:
    try:
        from .universal_sso import verify_universal_token
    except (ImportError, ValueError):
        try:
            from utils.universal_sso import verify_universal_token
        except (ImportError, ValueError):
            import sys
            from pathlib import Path
            _shared_dir = str(Path(__file__).resolve().parent.parent.parent / 'shared')
            if _shared_dir not in sys.path:
                sys.path.insert(0, _shared_dir)
            from universal_sso import verify_universal_token
except Exception:
    verify_universal_token = None

class AuthManager:
    SESSION_DURATION = 30 * 24 * 3600  # 30 days in seconds

    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT,
                    display_name TEXT,
                    avatar_url TEXT,
                    password_hash TEXT,
                    salt TEXT,
                    created_at REAL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at REAL,
                    expires_at REAL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)')
            conn.commit()

    @staticmethod
    def hash_password(password: str, salt_hex: str) -> str:
        salt = bytes.fromhex(salt_hex)
        return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex()

    def register_user(self, username: str, password: str, email: str = None, display_name: str = None) -> dict:
        clean_user = str(username or "").strip().lower()
        if not clean_user or len(clean_user) < 3:
            raise ValueError("Tên đăng nhập phải có ít nhất 3 ký tự.")
        if not password or len(password) < 6:
            raise ValueError("Mật khẩu phải có ít nhất 6 ký tự.")

        clean_email = str(email or "").strip().lower() if email else None
        clean_name = str(display_name or "").strip() or clean_user

        salt = secrets.token_hex(16)
        pwd_hash = self.hash_password(password, salt)
        user_id = str(uuid.uuid4())
        now = time.time()

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (id, username, email, display_name, avatar_url, password_hash, salt, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (user_id, clean_user, clean_email, clean_name, None, pwd_hash, salt, now)
                )
                conn.commit()
                return {
                    "id": user_id,
                    "username": clean_user,
                    "email": clean_email,
                    "display_name": clean_name,
                    "avatar_url": None,
                    "created_at": now
                }
        except sqlite3.IntegrityError as err:
            if "UNIQUE" in str(err):
                raise ValueError("Tên đăng nhập hoặc email đã được sử dụng.")
            raise

    def authenticate_user(self, identifier: str, password: str) -> dict | None:
        clean_id = str(identifier or "").strip().lower()
        if not clean_id or not password:
            return None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, email, display_name, avatar_url, password_hash, salt, created_at "
                "FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?",
                (clean_id, clean_id)
            )
            row = cursor.fetchone()
            if not row:
                return None

            expected_hash = self.hash_password(password, row["salt"])
            if not secrets.compare_digest(expected_hash, row["password_hash"]):
                return None

            user_dict = {
                "id": row["id"],
                "username": row["username"],
                "email": row["email"],
                "display_name": row["display_name"] or row["username"],
                "avatar_url": row["avatar_url"],
                "created_at": row["created_at"]
            }

            token = self._create_session(conn, user_dict["id"])
            return {"token": token, "user": user_dict}

    def google_auth(self, email: str, display_name: str = None, avatar_url: str = None) -> dict:
        clean_email = str(email or "").strip().lower()
        if not clean_email:
            raise ValueError("Google email cannot be empty.")

        clean_name = str(display_name or "").strip() or clean_email.split("@")[0]
        now = time.time()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, email, display_name, avatar_url, created_at FROM users "
                "WHERE LOWER(email) = ? OR LOWER(username) = ?",
                (clean_email, clean_email)
            )
            row = cursor.fetchone()

            if row:
                user_id = row["id"]
                # Update display name or avatar if provided
                cursor.execute(
                    "UPDATE users SET display_name = COALESCE(?, display_name), "
                    "avatar_url = COALESCE(?, avatar_url) WHERE id = ?",
                    (clean_name, avatar_url, user_id)
                )
                conn.commit()
                user_dict = {
                    "id": user_id,
                    "username": row["username"],
                    "email": row["email"] or clean_email,
                    "display_name": clean_name or row["display_name"],
                    "avatar_url": avatar_url or row["avatar_url"],
                    "created_at": row["created_at"]
                }
            else:
                user_id = str(uuid.uuid4())
                salt = secrets.token_hex(16)
                dummy_pwd = secrets.token_hex(32)
                pwd_hash = self.hash_password(dummy_pwd, salt)
                cursor.execute(
                    "INSERT INTO users (id, username, email, display_name, avatar_url, password_hash, salt, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (user_id, clean_email, clean_email, clean_name, avatar_url, pwd_hash, salt, now)
                )
                conn.commit()
                user_dict = {
                    "id": user_id,
                    "username": clean_email,
                    "email": clean_email,
                    "display_name": clean_name,
                    "avatar_url": avatar_url,
                    "created_at": now
                }

            token = self._create_session(conn, user_id)
            return {"token": token, "user": user_dict}

    def verify_google_credential(self, credential: str) -> dict:
        if not credential:
            raise ValueError("Missing Google credential.")

        # 1. Try remote verification via Google's tokeninfo endpoint for cryptographic validity
        try:
            req_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}"
            req = urllib.request.Request(req_url, headers={"User-Agent": "Meikova Harvest/2.0.5"})
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    email = data.get("email")
                    if email:
                        return {
                            "email": email,
                            "display_name": data.get("name") or data.get("given_name") or email.split("@")[0],
                            "avatar_url": data.get("picture")
                        }
        except Exception:
            pass

        # 2. Local fallback decode (standard JWT format: header.payload.signature)
        parts = credential.split(".")
        if len(parts) >= 2:
            payload_b64 = parts[1]
            # Add padding
            rem = len(payload_b64) % 4
            if rem:
                payload_b64 += "=" * (4 - rem)
            try:
                payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
                email = payload.get("email")
                if email:
                    return {
                        "email": email,
                        "display_name": payload.get("name") or email.split("@")[0],
                        "avatar_url": payload.get("picture")
                    }
            except Exception as e:
                raise ValueError(f"Không thể giải mã Google token: {e}")

        raise ValueError("Google token không hợp lệ hoặc thiếu thông tin email.")

    def _create_session(self, conn, user_id: str) -> str:
        token = secrets.token_hex(32)
        now = time.time()
        expires_at = now + self.SESSION_DURATION
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, now, expires_at)
        )
        conn.commit()
        return token

    def validate_session(self, token: str) -> dict | None:
        if not token:
            return None

        # 1. Fast-path: Check if token is a Universal SSO Ed25519 Token (offline 0.1ms verification)
        if verify_universal_token and token.count('.') == 2:
            sso_user = verify_universal_token(token)
            if sso_user:
                return {
                    'id': sso_user.get('sub'),
                    'username': sso_user.get('username'),
                    'email': sso_user.get('email'),
                    'display_name': sso_user.get('display_name') or sso_user.get('username'),
                    'avatar_url': None,
                    'created_at': sso_user.get('iat', time.time())
                }

        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT u.id, u.username, u.email, u.display_name, u.avatar_url, u.created_at, s.expires_at "
                "FROM sessions s "
                "JOIN users u ON s.user_id = u.id "
                "WHERE s.token = ? AND s.expires_at > ?",
                (token, now)
            )
            row = cursor.fetchone()
            if not row:
                return None

            return {
                "id": row["id"],
                "username": row["username"],
                "email": row["email"],
                "display_name": row["display_name"] or row["username"],
                "avatar_url": row["avatar_url"],
                "created_at": row["created_at"]
            }

    def delete_session(self, token: str) -> bool:
        if not token:
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return cursor.rowcount > 0

    def claim_guest_history(self, user_id: str, download_ids: list = None) -> int:
        if not user_id:
            return 0
        from utils.db import HarvestDbAdapter
        db = HarvestDbAdapter(self.db_path)
        claimed_count = 0
        try:
            if download_ids:
                placeholders = ",".join("?" for _ in download_ids)
                rows = db.fetchall(f"SELECT download_id, data FROM downloads WHERE user_id IS NULL AND download_id IN ({placeholders})", tuple(download_ids))
            else:
                rows = db.fetchall("SELECT download_id, data FROM downloads WHERE user_id IS NULL")

            for row in rows:
                d_id = row[0]
                data_str = row[1]
                try:
                    d = json.loads(data_str) if data_str else {}
                    d["user_id"] = user_id
                    d["sync_status"] = "synced"
                    db.execute(
                        "UPDATE downloads SET user_id = ?, data = ?, sync_status = 'synced' WHERE download_id = ?",
                        (user_id, json.dumps(d), d_id)
                    )
                    claimed_count += 1
                except Exception:
                    db.execute(
                        "UPDATE downloads SET user_id = ?, sync_status = 'synced' WHERE download_id = ?",
                        (user_id, d_id)
                    )
                    claimed_count += 1

            if db.is_turso:
                try:
                    with self._get_connection() as conn:
                        cursor = conn.cursor()
                        if download_ids:
                            placeholders = ",".join("?" for _ in download_ids)
                            cursor.execute(f"SELECT download_id, data FROM downloads WHERE user_id IS NULL AND download_id IN ({placeholders})", download_ids)
                        else:
                            cursor.execute("SELECT download_id, data FROM downloads WHERE user_id IS NULL")
                        for d_id, data_str in cursor.fetchall():
                            try:
                                d = json.loads(data_str) if data_str else {}
                                d["user_id"] = user_id
                                d["sync_status"] = "synced"
                                cursor.execute(
                                    "UPDATE downloads SET user_id = ?, data = ?, sync_status = 'synced' WHERE download_id = ?",
                                    (user_id, json.dumps(d), d_id)
                                )
                            except Exception:
                                cursor.execute(
                                    "UPDATE downloads SET user_id = ?, sync_status = 'synced' WHERE download_id = ?",
                                    (user_id, d_id)
                                )
                        conn.commit()
                except Exception:
                    pass
            return claimed_count
        finally:
            db.close()
