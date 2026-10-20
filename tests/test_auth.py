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
            display_name="Dev Titan",
            avatar_url="https://lh3.googleusercontent.com/photo.jpg"
        )
        self.assertIsNotNone(auth_res)
        self.assertEqual(auth_res["user"]["email"], "developer@gmail.com")
        self.assertEqual(auth_res["user"]["display_name"], "Dev Titan")

        # Repeat Google login should not create duplicate user, should return same user ID
        auth_res_2 = auth_mgr.google_auth(
            email="developer@gmail.com",
            display_name="Dev Titan Updated",
            avatar_url="https://lh3.googleusercontent.com/photo_new.jpg"
        )
        self.assertEqual(auth_res_2["user"]["id"], auth_res["user"]["id"])
        self.assertEqual(auth_res_2["user"]["display_name"], "Dev Titan Updated")

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

            # 3. /api/auth/login endpoint
            res = client.post("/api/auth/login", json={
                "username": "api_user",
                "password": "Password123!"
            })
            self.assertEqual(res.status_code, 200)
            login_data = res.get_json()
            self.assertEqual(login_data["status"], "success")

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


if __name__ == "__main__":
    unittest.main()
