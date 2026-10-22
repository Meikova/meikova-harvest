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
                    gateway_user_id TEXT,
                    auth_provider TEXT DEFAULT 'local',
                    sync_status TEXT DEFAULT 'synced',
                    created_at REAL,
                    updated_at REAL
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
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auth_sync_queue (
                    id TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    user_id TEXT,
                    payload TEXT NOT NULL,
                    status TEXT DEFAULT 'PENDING',
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            ''')
            migrations = [
                "ALTER TABLE users ADD COLUMN gateway_user_id TEXT;",
                "ALTER TABLE users ADD COLUMN auth_provider TEXT DEFAULT 'local';",
                "ALTER TABLE users ADD COLUMN sync_status TEXT DEFAULT 'synced';",
                "ALTER TABLE users ADD COLUMN updated_at REAL;",
            ]
            for sql in migrations:
                try:
                    cursor.execute(sql)
                except sqlite3.OperationalError:
                    pass

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_harvest_users_gateway ON users(gateway_user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_harvest_sync_queue_status ON auth_sync_queue(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)')
            conn.commit()

    def queue_auth_sync(self, action: str, user_id: str | None, payload: dict | str) -> str:
        sync_id = str(uuid.uuid4())
        now = time.time()
        payload_str = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO auth_sync_queue (id, action, user_id, payload, status, retry_count, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, 'PENDING', 0, ?, ?)",
                (sync_id, action, user_id, payload_str, now, now)
            )
            conn.commit()
        return sync_id

    def get_auth_sync_queue(self, status: str = 'PENDING') -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, action, user_id, payload, status, retry_count, created_at FROM auth_sync_queue "
                "WHERE status = ? ORDER BY created_at ASC",
                (status,)
            )
            rows = cursor.fetchall()
            items = []
            for r in rows:
                p = r["payload"]
                try:
                    p = json.loads(p)
                except Exception:
                    pass
                items.append({
                    "id": r["id"],
                    "action": r["action"],
                    "user_id": r["user_id"],
                    "payload": p,
                    "status": r["status"],
                    "retry_count": r["retry_count"],
                    "created_at": r["created_at"],
                })
            return items

    def mark_auth_sync_status(self, sync_id: str, status: str, error_msg: str | None = None):
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE auth_sync_queue SET status = ?, error_message = ?, updated_at = ? WHERE id = ?",
                (status, error_msg, now, sync_id)
            )
            conn.commit()

    def get_sync_status(self) -> dict:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM auth_sync_queue WHERE status = 'PENDING'")
            pending = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM auth_sync_queue WHERE status = 'SYNCED'")
            synced = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM auth_sync_queue WHERE status = 'FAILED'")
            failed = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE sync_status = 'pending_gateway'")
            pending_users = cursor.fetchone()[0]
            return {
                "queue_count": pending,
                "synced_count": synced,
                "failed_count": failed,
                "pending_users": pending_users,
            }

    def find_user_by_identifier(self, identifier: str) -> dict | None:
        if not identifier:
            return None
        raw = str(identifier).strip()
        lower = raw.lower()
        prefix = lower.split('@')[0] if '@' in lower else lower

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, email, display_name, avatar_url, password_hash, salt, gateway_user_id, auth_provider, sync_status, created_at "
                "FROM users WHERE id = ? OR gateway_user_id = ?",
                (raw, raw)
            )
            row = cursor.fetchone()
            if not row:
                cursor.execute(
                    "SELECT id, username, email, display_name, avatar_url, password_hash, salt, gateway_user_id, auth_provider, sync_status, created_at "
                    "FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?",
                    (lower, lower)
                )
                row = cursor.fetchone()
            if not row:
                cursor.execute(
                    "SELECT id, username, email, display_name, avatar_url, password_hash, salt, gateway_user_id, auth_provider, sync_status, created_at "
                    "FROM users WHERE LOWER(username) = ? OR LOWER(email) LIKE ?",
                    (prefix, f"{prefix}@%")
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
                "password_hash": row["password_hash"],
                "salt": row["salt"],
                "gateway_user_id": row["gateway_user_id"],
                "auth_provider": row["auth_provider"],
                "sync_status": row["sync_status"],
                "created_at": row["created_at"],
            }

    def upsert_local_user_from_sso(self, sso_user: dict) -> dict:
        if not sso_user or not sso_user.get("sub"):
            return {}
        sub = str(sso_user["sub"]).strip()
        clean_user = str(sso_user.get("username") or sub).strip().lower()
        clean_email = str(sso_user.get("email") or "").strip().lower() or None
        disp = str(sso_user.get("display_name") or sso_user.get("username") or clean_user).strip()
        now = time.time()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, email FROM users WHERE id = ? OR gateway_user_id = ?", (sub, sub))
            existing = cursor.fetchone()

            if not existing and clean_email:
                cursor.execute("SELECT id, username, email FROM users WHERE LOWER(email) = ?", (clean_email,))
                existing = cursor.fetchone()

            if not existing:
                cursor.execute("SELECT id, username, email FROM users WHERE LOWER(username) = ?", (clean_user,))
                existing = cursor.fetchone()

            if existing:
                user_id = existing["id"]
                cursor.execute(
                    "UPDATE users SET gateway_user_id = ?, email = COALESCE(?, email), display_name = ?, "
                    "auth_provider = 'universal_sso', sync_status = 'synced', updated_at = ? WHERE id = ?",
                    (sub, clean_email, disp, now, user_id)
                )
                conn.commit()
                return {
                    "id": user_id,
                    "gateway_user_id": sub,
                    "username": existing["username"],
                    "email": clean_email or existing["email"],
                    "display_name": disp,
                    "avatar_url": None,
                    "created_at": now
                }

            dummy_salt = secrets.token_hex(16)
            dummy_hash = self.hash_password(secrets.token_hex(32), dummy_salt)
            cursor.execute(
                "INSERT INTO users (id, username, email, display_name, avatar_url, password_hash, salt, gateway_user_id, auth_provider, sync_status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'universal_sso', 'synced', ?, ?)",
                (sub, clean_user, clean_email, disp, None, dummy_hash, dummy_salt, sub, now, now)
            )
            conn.commit()
            return {
                "id": sub,
                "gateway_user_id": sub,
                "username": clean_user,
                "email": clean_email,
                "display_name": disp,
                "avatar_url": None,
                "created_at": now
            }

    def link_gateway_account(self, data: dict) -> dict:
        sub = str(data.get("gateway_user_id") or data.get("sub") or data.get("id") or "").strip()
        if not sub:
            return {"action": "ERROR", "message": "Missing gateway_user_id"}
        clean_email = str(data.get("email") or "").strip().lower() or None
        clean_user = str(data.get("username") or sub).strip().lower()
        disp = str(data.get("display_name") or data.get("name") or clean_user).strip()
        now = time.time()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Case 1: Same Email -> Account Linking
            if clean_email:
                cursor.execute("SELECT id, username, email FROM users WHERE LOWER(email) = ?", (clean_email,))
                local_email_match = cursor.fetchone()
                if local_email_match:
                    local_id = local_email_match["id"]
                    cursor.execute(
                        "UPDATE users SET gateway_user_id = ?, auth_provider = 'universal_sso', sync_status = 'synced', updated_at = ? WHERE id = ?",
                        (sub, now, local_id)
                    )
                    conn.commit()
                    return {"action": "LINKED", "user_id": sub, "local_id": local_id}

            # Case 2: Same Username, different Email -> Namespace Resolution
            cursor.execute("SELECT id, username, email FROM users WHERE LOWER(username) = ?", (clean_user,))
            local_user_match = cursor.fetchone()
            if local_user_match and (not clean_email or (local_user_match["email"] or "").lower() != clean_email):
                local_id = local_user_match["id"]
                suffix = secrets.token_hex(3)
                renamed_username = f"{local_user_match['username']}_local_{suffix}"
                cursor.execute(
                    "UPDATE users SET username = ?, sync_status = 'conflict', updated_at = ? WHERE id = ?",
                    (renamed_username, now, local_id)
                )
                conn.commit()

                # Insert fresh gateway user
                self.upsert_local_user_from_sso({
                    "sub": sub,
                    "username": clean_user,
                    "email": clean_email,
                    "display_name": disp,
                })
                return {"action": "RESOLVED_NAMESPACE", "local_renamed_to": renamed_username, "user_id": sub}

        # Case 3: Fresh insert
        self.upsert_local_user_from_sso({
            "sub": sub,
            "username": clean_user,
            "email": clean_email,
            "display_name": disp,
        })
        return {"action": "INSERTED", "user_id": sub}

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
                    "INSERT INTO users (id, username, email, display_name, avatar_url, password_hash, salt, auth_provider, sync_status, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, 'local', 'pending_gateway', ?, ?)",
                    (user_id, clean_user, clean_email, clean_name, None, pwd_hash, salt, now, now)
                )
                conn.commit()

            # Enqueue for gateway synchronization
            self.queue_auth_sync('REGISTER', user_id, {
                "id": user_id,
                "username": clean_user,
                "email": clean_email,
                "created_at": now
            })

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
        user = self.find_user_by_identifier(identifier)
        if not user or not password:
            return None

        salt = user.get("salt")
        pwd_hash = user.get("password_hash")
        if not salt or not pwd_hash:
            return None

        expected_hash = self.hash_password(password, salt)
        if not secrets.compare_digest(expected_hash, pwd_hash):
            return None

        user_dict = {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "display_name": user["display_name"] or user["username"],
            "avatar_url": user["avatar_url"],
            "created_at": user["created_at"]
        }

        with self._get_connection() as conn:
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
            req = urllib.request.Request(req_url, headers={"User-Agent": "Meikova Harvest/2.0.7"})
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
                local_u = self.upsert_local_user_from_sso(sso_user)
                return {
                    'id': local_u.get('id', sso_user.get('sub')),
                    'username': local_u.get('username', sso_user.get('username')),
                    'email': local_u.get('email', sso_user.get('email')),
                    'display_name': local_u.get('display_name') or sso_user.get('display_name') or sso_user.get('username'),
                    'avatar_url': local_u.get('avatar_url'),
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
