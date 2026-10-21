import os
import unittest
import tempfile
import sqlite3
import json
import time
from unittest.mock import patch, MagicMock

class TestAuthModule(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_auth.db")

    def tearDown(self):
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            os.rmdir(self.temp_dir)
        except Exception:
            pass

    def test_auth_manager_register_and_login(self):
        # Import target auth manager module
        from utils.auth import AuthManager
        auth_mgr = AuthManager(self.db_path)
        
        # 1. Register new user
        user = auth_mgr.register_user("testuser", "securePassword123", email="test@example.com", display_name="Test User")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "testuser")
        self.assertEqual(user["email"], "test@example.com")
        self.assertIn("id", user)

        # 2. Duplicate registration should raise error
        with self.assertRaises(ValueError):
            auth_mgr.register_user("testuser", "anotherPassword")

        # 3. Successful login
        auth_res = auth_mgr.authenticate_user("testuser", "securePassword123")
        self.assertIsNotNone(auth_res)
        self.assertIn("token", auth_res)
        self.assertEqual(auth_res["user"]["username"], "testuser")

        # 4. Failed login
        bad_auth = auth_mgr.authenticate_user("testuser", "wrongPassword")
        self.assertIsNone(bad_auth)

        # 5. Validate session token
        session_user = auth_mgr.validate_session(auth_res["token"])
        self.assertIsNotNone(session_user)
        self.assertEqual(session_user["id"], user["id"])

        # 6. Logout / Delete session
        auth_mgr.delete_session(auth_res["token"])
        self.assertIsNone(auth_mgr.validate_session(auth_res["token"]))

    def test_google_auth(self):
        from utils.auth import AuthManager
        auth_mgr = AuthManager(self.db_path)

        # Simulate Google user login
        auth_res = auth_mgr.google_auth(
            email="developer@gmail.com",
            display_name="Dev Meikova",
            avatar_url="https://lh3.googleusercontent.com/photo.jpg"
        )
        self.assertIsNotNone(auth_res)
        self.assertEqual(auth_res["user"]["email"], "developer@gmail.com")
        self.assertEqual(auth_res["user"]["display_name"], "Dev Meikova")

        # Repeat Google login should not create duplicate user, should return same user ID
        auth_res_2 = auth_mgr.google_auth(
            email="developer@gmail.com",
            display_name="Dev Meikova Updated",
            avatar_url="https://lh3.googleusercontent.com/photo_new.jpg"
        )
        self.assertEqual(auth_res_2["user"]["id"], auth_res["user"]["id"])
        self.assertEqual(auth_res_2["user"]["display_name"], "Dev Meikova Updated")

    def test_history_isolated_by_user(self):
        from config import PersistentDownloadStatus
        from utils.auth import AuthManager

        auth_mgr = AuthManager(self.db_path)
        u1 = auth_mgr.register_user("user_one", "pass123456")
        u2 = auth_mgr.register_user("user_two", "pass123456")

        status_mgr = PersistentDownloadStatus(self.db_path)
        
        # Save task for user 1
        status_mgr._save_task("task_u1", {
            "title": "User 1 Video",
            "status": "complete",
            "user_id": u1["id"],
            "timestamp": time.time()
        })

        # Save task for user 2
        status_mgr._save_task("task_u2", {
            "title": "User 2 Video",
            "status": "complete",
            "user_id": u2["id"],
            "timestamp": time.time()
        })

        # Save guest task
        status_mgr._save_task("task_guest", {
            "title": "Guest Video",
            "status": "complete",
            "user_id": None,
            "timestamp": time.time()
        })

        # Query history for user 1
        h1 = status_mgr.get_history(limit=10, user_id=u1["id"])
        h1_ids = [item.get("download_id") for item in h1]
        self.assertIn("task_u1", h1_ids)
        self.assertNotIn("task_u2", h1_ids)

        # Query history for user 2
        h2 = status_mgr.get_history(limit=10, user_id=u2["id"])
        h2_ids = [item.get("download_id") for item in h2]
        self.assertIn("task_u2", h2_ids)
        self.assertNotIn("task_u1", h2_ids)

    def test_flask_auth_routes(self):
        from flask import Flask
        from routes.auth import auth_bp
        from utils.auth import AuthManager

        app = Flask(__name__)
        app.register_blueprint(auth_bp)
        client = app.test_client()

        # Patch config.auth_manager to use our test DB
        test_auth_mgr = AuthManager(self.db_path)
        with patch("routes.auth.auth_manager", test_auth_mgr):
            # 1. Register endpoint
            res = client.post("/api/auth/register", json={
                "username": "api_user",
                "password": "Password123!",
                "email": "api_user@test.com"
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data["status"], "success")
            token = data["token"]

            # 2. /api/auth/me with Bearer token
            res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(res.status_code, 200)
            me_data = res.get_json()
            self.assertEqual(me_data["user"]["username"], "api_user")

            # 3. /api/auth/login endpoint (test username, username_or_email, and email)
            res = client.post("/api/auth/login", json={
                "username": "api_user",
                "password": "Password123!"
            })
            self.assertEqual(res.status_code, 200)
            login_data = res.get_json()
            self.assertEqual(login_data["status"], "success")

            # 3b. /api/auth/login with username_or_email field
            res_uoe = client.post("/api/auth/login", json={
                "username_or_email": "api_user",
                "password": "Password123!"
            })
            self.assertEqual(res_uoe.status_code, 200)
            self.assertEqual(res_uoe.get_json()["status"], "success")

            # 3c. /api/auth/login with email
            res_email = client.post("/api/auth/login", json={
                "username_or_email": "api_user@test.com",
                "password": "Password123!"
            })
            self.assertEqual(res_email.status_code, 200)
            self.assertEqual(res_email.get_json()["status"], "success")

            # 4. /api/auth/logout endpoint
            res = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(res.status_code, 200)

            # 5. /api/auth/me after logout should return 401
            res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(res.status_code, 401)

    def test_google_start_and_poll_flow(self):
        from flask import Flask
        from routes.auth import auth_bp, fulfill_auth_request
        from utils.auth import AuthManager

        app = Flask(__name__)
        app.register_blueprint(auth_bp)
        client = app.test_client()

        # 1. /api/auth/google/start?mode=mobile
        res = client.get("/api/auth/google/start?mode=mobile")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("auth_url", data)
        self.assertIn("state", data)
        self.assertTrue(data["state"].startswith("mobile_"))
        state = data["state"]

        # 2. Poll before completion -> pending
        poll_res = client.get(f"/api/auth/google/poll?state={state}")
        self.assertEqual(poll_res.status_code, 200)
        self.assertEqual(poll_res.get_json()["status"], "pending")

        # 3. Fulfill request
        fulfill_auth_request(state, {
            "token": "test_mobile_jwt_token",
            "user": {"id": 99, "email": "mobile@test.com", "display_name": "Mobile Tester"}
        })

        # 4. Poll after completion -> ok and popped
        poll_res2 = client.get(f"/api/auth/google/poll?state={state}")
        self.assertEqual(poll_res2.status_code, 200)
        p2_data = poll_res2.get_json()
        self.assertEqual(p2_data["status"], "ok")
        self.assertEqual(p2_data["token"], "test_mobile_jwt_token")
        self.assertEqual(p2_data["user"]["email"], "mobile@test.com")

        # 5. Poll again -> pending (since it was popped)
        poll_res3 = client.get(f"/api/auth/google/poll?state={state}")
        self.assertEqual(poll_res3.get_json()["status"], "pending")


    def test_google_redirect_uri_reverse_proxy(self):
        from flask import Flask
        from routes.auth import auth_bp

        app = Flask(__name__)
        app.register_blueprint(auth_bp)
        client = app.test_client()

        # 1. Cloud domain -> HTTPS
        res = client.get('/api/auth/google/start?mode=web', headers={'Host': 'meikova-harvest.onrender.com'})
        self.assertEqual(res.status_code, 200)
        self.assertIn('https%3A%2F%2Fmeikova-harvest.onrender.com%2Fapi%2Fauth%2Fgoogle%2Fcallback', res.get_json()['auth_url'])

        # 2. X-Forwarded-Proto -> HTTPS
        res2 = client.get('/api/auth/google/start?mode=web', headers={'Host': 'custom-domain.com', 'X-Forwarded-Proto': 'https'})
        self.assertEqual(res2.status_code, 200)
        self.assertIn('https%3A%2F%2Fcustom-domain.com%2Fapi%2Fauth%2Fgoogle%2Fcallback', res2.get_json()['auth_url'])

        # 3. Localhost -> HTTP
        res3 = client.get('/api/auth/google/start?mode=web', headers={'Host': 'localhost:5000'})
        self.assertEqual(res3.status_code, 200)
        self.assertIn('http%3A%2F%2Flocalhost%3A5000%2Fapi%2Fauth%2Fgoogle%2Fcallback', res3.get_json()['auth_url'])

    def test_guest_history_isolation_and_clear(self):
        from config import PersistentDownloadStatus
        from utils.auth import AuthManager

        auth_mgr = AuthManager(self.db_path)
        u1 = auth_mgr.register_user("u_isolated_1", "pass123456")
        status_mgr = PersistentDownloadStatus(self.db_path)

        # 1. Seed tasks
        status_mgr._save_task("task_user_secret", {
            "title": "Private User Video",
            "status": "complete",
            "user_id": u1["id"],
            "timestamp": time.time()
        })
        status_mgr._save_task("task_guest_public", {
            "title": "Guest Video",
            "status": "complete",
            "user_id": None,
            "timestamp": time.time()
        })

        # 2. Guest query (user_id=None) MUST NOT return registered user's private video!
        guest_h = status_mgr.get_history(limit=10, user_id=None)
        guest_ids = [item.get("download_id") for item in guest_h]
        self.assertIn("task_guest_public", guest_ids)
        self.assertNotIn("task_user_secret", guest_ids)

        # 3. Clear guest history MUST NOT delete user's private video!
        status_mgr.clear_history(user_id=None)
        
        user_h = status_mgr.get_history(limit=10, user_id=u1["id"])
        user_ids = [item.get("download_id") for item in user_h]
        self.assertIn("task_user_secret", user_ids, "Private user video was accidentally deleted when guest cleared history!")

    def test_claim_guest_history_deep_sync(self):
        from config import PersistentDownloadStatus
        from utils.auth import AuthManager

        auth_mgr = AuthManager(self.db_path)
        u1 = auth_mgr.register_user("u_claim_target", "pass123456")
        status_mgr = PersistentDownloadStatus(self.db_path)

        # Seed guest tasks
        status_mgr._save_task("guest_item_1", {
            "title": "Guest 1",
            "status": "complete",
            "user_id": None,
            "timestamp": time.time()
        })
        status_mgr._save_task("guest_item_2", {
            "title": "Guest 2",
            "status": "complete",
            "user_id": None,
            "timestamp": time.time()
        })

        # Claim specific item
        claimed = auth_mgr.claim_guest_history(u1["id"], download_ids=["guest_item_1"])
        self.assertEqual(claimed, 1)

        # Verify guest_item_1 belongs to u1, but guest_item_2 is still guest
        u1_history = status_mgr.get_history(limit=10, user_id=u1["id"])
        u1_ids = [x["download_id"] for x in u1_history]
        self.assertIn("guest_item_1", u1_ids)
        self.assertNotIn("guest_item_2", u1_ids)

        # Verify JSON data inside task was also updated with user_id
        task_1 = status_mgr.get("guest_item_1")
        self.assertEqual(task_1.get("user_id"), u1["id"])

    def test_download_ownership_access_control(self):
        from flask import Flask
        from routes.download import download_bp, check_task_ownership
        from routes.auth import auth_bp
        from utils.auth import AuthManager
        from config import downloads_status, downloads_status_lock

        app = Flask(__name__)
        app.register_blueprint(auth_bp)
        app.register_blueprint(download_bp)
        client = app.test_client()

        auth_mgr = AuthManager(self.db_path)
        u_alice = auth_mgr.register_user("alice", "pass123456")
        u_bob = auth_mgr.register_user("bob", "pass123456")

        alice_token = auth_mgr.authenticate_user("alice", "pass123456")["token"]
        bob_token = auth_mgr.authenticate_user("bob", "pass123456")["token"]

        with downloads_status_lock:
            downloads_status["task_alice_owned"] = {
                "status": "downloading",
                "progress": 42,
                "user_id": u_alice["id"],
                "filepath": "/nonexistent/test.mp4",
                "filename": "test.mp4",
                "title": "Alice Private Video"
            }

        with patch("routes.auth.auth_manager", auth_mgr):
            # 1. Bob tries to cancel Alice's task -> 403 Forbidden
            res = client.post("/api/download/cancel/task_alice_owned", headers={"Authorization": f"Bearer {bob_token}"})
            self.assertEqual(res.status_code, 403)

            # 2. Guest tries to delete Alice's task -> 403 Forbidden
            res2 = client.post("/api/download/history/delete/task_alice_owned")
            self.assertEqual(res2.status_code, 403)

            # 3. Alice cancels her own task -> 200 OK
            res3 = client.post("/api/download/cancel/task_alice_owned", headers={"Authorization": f"Bearer {alice_token}"})
            self.assertEqual(res3.status_code, 200)
            self.assertEqual(downloads_status["task_alice_owned"]["status"], "cancelled")

if __name__ == "__main__":
    unittest.main()
