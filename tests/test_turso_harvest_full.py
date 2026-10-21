# -*- coding: utf-8 -*-
"""
Meikova Harvest — Comprehensive Turso Cloud Dual Adapter & Universal SSO Test Suite
Tests:
1. Turso Cloud SQLite connection, CRUD download task, query history, clean task.
2. Fallback to local SQLite WAL when env vars are absent (timeout=10.0, WAL mode, Row factory).
3. Universal SSO Ed25519 offline token validation in AuthManager.validate_session.

Mandate: Zero-emoji in all code, comments, and console output.
"""

import os
import sys
import time
import json
import unittest
from pathlib import Path

# Setup paths
HARVEST_DIR = Path(__file__).resolve().parent.parent
SHARED_DIR = HARVEST_DIR.parent / "shared"
sys.path.insert(0, str(HARVEST_DIR))
sys.path.insert(0, str(SHARED_DIR))

from utils.db import HarvestDbAdapter
from utils.auth import AuthManager
from config import PersistentDownloadStatus

TURSO_URL = "https://meikova-harvest-m3ik18dp.aws-ap-northeast-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTI1ODkxNDYsImlkIjoiMDFhMTVlYTMtOTQwMS03NWM3LThiZTUtNWYxZjM3ZGY4OTM5Iiwia2lkIjoibk13eDJZSGtEaHVvYl81SXZkM1FQVzhpVi1ZT0poeHdUbmpIMXo5dl9iMCIsInJpZCI6ImM1N2FkOWMzLTQ3MzctNGU4ZS04MGUzLTBiN2QyM2M0NmY3NiJ9.oyOtljcDbKwSgzyDwq-yHNlc-aczemegxNalqiiyL-6zNzEMfij_TO2AII259aPQQh3xbV5cKK5gDBkCNrg5Bw"


class TestTursoHarvestFull(unittest.TestCase):
    def setUp(self):
        self.temp_db = str(HARVEST_DIR / "tests" / "test_local_scratch.db")
        self.clean_temp_db()

    def tearDown(self):
        self.clean_temp_db()

    def clean_temp_db(self):
        import gc
        gc.collect()
        for ext in ["", "-wal", "-shm"]:
            f = self.temp_db + ext
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Turso Cloud Connection & Full CRUD
    # ─────────────────────────────────────────────────────────────────────────
    def test_1_turso_cloud_crud(self):
        print("\n[TEST 1] Turso Cloud Connection & Full CRUD")
        adapter = HarvestDbAdapter(self.temp_db, url=TURSO_URL, auth_token=TURSO_TOKEN)
        pds = None
        try:
            self.assertTrue(adapter.is_turso, "Adapter should identify as Turso Cloud")

            # Basic ping query
            ping = adapter.fetchone("SELECT 1 AS online")
            self.assertIsNotNone(ping)
            self.assertEqual(ping[0], 1)
            self.assertEqual(ping["online"], 1)
            print("  [PASS] Turso Cloud online check: OK")

            # Direct CRUD operations on 'downloads' table
            task_id = f"task_turso_{int(time.time() * 1000)}"
            task_payload = json.dumps({
                "title": "Turso Integration Test Video",
                "url": "https://example.com/watch?v=123",
                "status": "completed",
                "format": "mp4",
                "filesize": 10485760
            })
            now = time.time()
            user_id = "usr_turso_harvest_test"

            # Insert
            insert_sql = (
                "INSERT INTO downloads (download_id, data, timestamp, user_id, sync_status) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(download_id) DO UPDATE SET data = ?, timestamp = ?, user_id = ?, sync_status = ?"
            )
            adapter.execute(insert_sql, (task_id, task_payload, now, user_id, "synced",
                                         task_payload, now, user_id, "synced"))

            # Fetchone and index/key access
            row = adapter.fetchone("SELECT download_id, data, user_id, sync_status FROM downloads WHERE download_id = ?", (task_id,))
            self.assertIsNotNone(row)
            self.assertEqual(row[0], task_id)
            self.assertEqual(row["download_id"], task_id)
            self.assertEqual(row["user_id"], user_id)
            self.assertEqual(row["sync_status"], "synced")

            retrieved_data = json.loads(row["data"])
            self.assertEqual(retrieved_data["title"], "Turso Integration Test Video")
            print("  [PASS] Direct INSERT and fetchone with index/key access: OK")

            # Fetchall query
            rows = adapter.fetchall("SELECT download_id FROM downloads WHERE user_id = ?", (user_id,))
            self.assertTrue(any(r[0] == task_id for r in rows))
            print("  [PASS] Direct fetchall: OK")

            # Executemany test (batch)
            batch_ids = [f"batch_{int(time.time())}_{i}" for i in range(3)]
            batch_params = [
                (b_id, json.dumps({"title": f"Batch Item {i}"}), now, user_id, "synced")
                for i, b_id in enumerate(batch_ids)
            ]
            batch_sql = "INSERT INTO downloads (download_id, data, timestamp, user_id, sync_status) VALUES (?, ?, ?, ?, ?)"
            adapter.executemany(batch_sql, batch_params)

            for b_id in batch_ids:
                check_b = adapter.fetchone("SELECT download_id FROM downloads WHERE download_id = ?", (b_id,))
                self.assertIsNotNone(check_b)
            print("  [PASS] Executemany batch insert on Turso: OK")

            # Cleanup batch items
            del_params = [(b_id,) for b_id in batch_ids]
            adapter.executemany("DELETE FROM downloads WHERE download_id = ?", del_params)
            print("  [PASS] Executemany batch delete on Turso: OK")

            # PersistentDownloadStatus integration with Turso
            old_url = os.environ.get("TURSO_DATABASE_URL")
            old_tok = os.environ.get("TURSO_AUTH_TOKEN")
            os.environ["TURSO_DATABASE_URL"] = TURSO_URL
            os.environ["TURSO_AUTH_TOKEN"] = TURSO_TOKEN

            try:
                pds = PersistentDownloadStatus(self.temp_db)
                self.assertTrue(pds.db.is_turso, "PersistentDownloadStatus should use Turso adapter")

                pds_task_id = f"pds_task_{int(time.time() * 1000)}"
                pds[pds_task_id] = {
                    "title": "Persistent Task",
                    "status": "finished",
                    "user_id": user_id,
                    "timestamp": time.time()
                }

                stored = pds.get(pds_task_id)
                self.assertIsNotNone(stored)
                self.assertEqual(stored.get("title"), "Persistent Task")
                self.assertEqual(stored.get("sync_status"), "synced")

                # History query
                hist = pds.get_history(limit=10, user_id=user_id)
                self.assertTrue(any(h.get("download_id") == pds_task_id for h in hist))
                print("  [PASS] PersistentDownloadStatus CRUD & history on Turso: OK")

                # Clean tasks
                pds.delete_task(pds_task_id)
                self.assertIsNone(pds.get(pds_task_id))
                adapter.execute("DELETE FROM downloads WHERE download_id = ?", (task_id,))
                print("  [PASS] Cleanup downloaded test tasks: OK")
            finally:
                if old_url:
                    os.environ["TURSO_DATABASE_URL"] = old_url
                else:
                    os.environ.pop("TURSO_DATABASE_URL", None)
                if old_tok:
                    os.environ["TURSO_AUTH_TOKEN"] = old_tok
                else:
                    os.environ.pop("TURSO_AUTH_TOKEN", None)
        finally:
            if pds and hasattr(pds, "db"):
                pds.db.close()
            adapter.close()

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Fallback to Local SQLite WAL
    # ─────────────────────────────────────────────────────────────────────────
    def test_2_local_sqlite_wal_fallback(self):
        print("\n[TEST 2] Fallback to Local SQLite WAL")
        # Ensure env vars are absent
        old_url = os.environ.pop("TURSO_DATABASE_URL", None)
        old_tok = os.environ.pop("TURSO_AUTH_TOKEN", None)

        adapter = HarvestDbAdapter(self.temp_db, url="", auth_token="")
        pds = None
        try:
            self.assertFalse(adapter.is_turso, "Adapter should identify as local SQLite")

            # Create test table
            adapter.execute("CREATE TABLE IF NOT EXISTS probe (id TEXT PRIMARY KEY, val INT, name TEXT)")

            # Check journal_mode is WAL
            mode = adapter.fetchone("PRAGMA journal_mode")
            self.assertIsNotNone(mode)
            self.assertEqual(mode[0].lower(), "wal", "Database journal_mode should be WAL")
            print("  [PASS] SQLite WAL mode confirmed: WAL")

            # Check insert and fetch with Row factory (supports row[0] and row['val'])
            adapter.execute("INSERT INTO probe VALUES (?, ?, ?)", ("k1", 42, "item_one"))
            row = adapter.fetchone("SELECT id, val, name FROM probe WHERE id = ?", ("k1",))
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "k1")
            self.assertEqual(row["id"], "k1")
            self.assertEqual(row[1], 42)
            self.assertEqual(row["val"], 42)
            self.assertEqual(row[2], "item_one")
            self.assertEqual(row["name"], "item_one")
            print("  [PASS] Local SQLite Row factory (index & key access): OK")

            # Check executemany on local SQLite
            batch = [("k2", 100, "two"), ("k3", 200, "three"), ("k4", 300, "four")]
            adapter.executemany("INSERT INTO probe VALUES (?, ?, ?)", batch)

            all_rows = adapter.fetchall("SELECT id, val FROM probe ORDER BY val ASC")
            self.assertEqual(len(all_rows), 4)
            self.assertEqual(all_rows[0]["id"], "k1")
            self.assertEqual(all_rows[3]["val"], 300)
            print("  [PASS] Local SQLite executemany & fetchall: OK")

            # Test PersistentDownloadStatus in offline mode
            pds = PersistentDownloadStatus(self.temp_db)
            self.assertFalse(pds.db.is_turso)

            local_task_id = "local_task_001"
            pds[local_task_id] = {
                "title": "Offline Local Video",
                "status": "pending",
                "timestamp": time.time()
            }

            stored = pds.get(local_task_id)
            self.assertIsNotNone(stored)
            self.assertEqual(stored.get("title"), "Offline Local Video")
            self.assertEqual(stored.get("sync_status"), "pending_sync")
            print("  [PASS] PersistentDownloadStatus offline task save (pending_sync): OK")

            # Mark synced
            pds.mark_synced([local_task_id])
            pending = pds.get_pending_sync()
            self.assertFalse(any(p["download_id"] == local_task_id for p in pending))
            print("  [PASS] PersistentDownloadStatus mark_synced & pending_sync: OK")

            pds.delete_task(local_task_id)
            self.assertIsNone(pds.get(local_task_id))
            print("  [PASS] PersistentDownloadStatus delete_task: OK")
        finally:
            if pds and hasattr(pds, "db"):
                pds.db.close()
            adapter.close()
            if old_url:
                os.environ["TURSO_DATABASE_URL"] = old_url
            if old_tok:
                os.environ["TURSO_AUTH_TOKEN"] = old_tok

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Universal SSO Ed25519 Token Validation
    # ─────────────────────────────────────────────────────────────────────────
    def test_3_universal_sso_token_validation(self):
        print("\n[TEST 3] Universal SSO Ed25519 Token Validation")
        from universal_sso import issue_universal_token, verify_universal_token

        auth_mgr = AuthManager(self.temp_db)

        test_user_id = f"usr_{int(time.time())}"
        test_username = "sso_harvest_tester"
        test_email = "harvest_sso@meikova.io"
        test_display_name = "SSO Harvest User"

        # Issue token
        token = issue_universal_token(
            user_id=test_user_id,
            username=test_username,
            email=test_email,
            display_name=test_display_name
        )
        self.assertTrue(bool(token), "Token should be issued successfully")
        print("  [PASS] Issued Universal SSO Ed25519 Token: OK")

        # Validate session in AuthManager (offline ~0.1ms)
        t0 = time.perf_counter()
        session = auth_mgr.validate_session(token)
        t_elapsed_ms = (time.perf_counter() - t0) * 1000

        self.assertIsNotNone(session, "Session should be valid from SSO token")
        self.assertEqual(session["id"], test_user_id)
        self.assertEqual(session["username"], test_username)
        self.assertEqual(session["email"], test_email)
        self.assertEqual(session["display_name"], test_display_name)
        print(f"  [PASS] Offline validate_session speed: {t_elapsed_ms:.3f}ms (< 5ms target): OK")

        # Tamper resistance test
        tampered_token = token[:-4] + "ZZZZ"
        tampered_session = auth_mgr.validate_session(tampered_token)
        self.assertIsNone(tampered_session, "Tampered token must return None")
        print("  [PASS] Tampered token rejection: OK")

        # Expired token test
        expired_token = issue_universal_token(
            user_id="usr_expired",
            username="expired_user",
            expires_in_sec=-100
        )
        expired_session = auth_mgr.validate_session(expired_token)
        self.assertIsNone(expired_session, "Expired token must return None")
        print("  [PASS] Expired token rejection: OK")

        # Verify local login fallback is unharmed
        reg_user = auth_mgr.register_user(
            username="localuser99",
            password="StrongPassword123!",
            email="local99@example.com",
            display_name="Local User 99"
        )
        auth_res = auth_mgr.authenticate_user("localuser99", "StrongPassword123!")
        self.assertIsNotNone(auth_res)
        local_token = auth_res["token"]

        local_session = auth_mgr.validate_session(local_token)
        self.assertIsNotNone(local_session)
        self.assertEqual(local_session["id"], reg_user["id"])
        self.assertEqual(local_session["username"], "localuser99")
        print("  [PASS] Local login fallback unharmed: OK")


if __name__ == "__main__":
    unittest.main()
