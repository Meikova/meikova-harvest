import os
import sys
import time
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app
from config import auth_manager

shared_priv = Path(__file__).resolve().parent.parent.parent / "shared" / "keys" / "ed25519_private.pem"
shared_pub = Path(__file__).resolve().parent.parent.parent / "shared" / "keys" / "ed25519_public.pem"

try:
    from utils.universal_sso import UniversalSSO
except ImportError:
    _shared_dir = str(Path(__file__).resolve().parent.parent.parent / 'shared')
    if _shared_dir not in sys.path:
        sys.path.insert(0, _shared_dir)
    from universal_sso import UniversalSSO

sso_signer = UniversalSSO()


class TestHarvestAuthSync(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_01_find_user_by_identifier(self):
        suffix = os.urandom(4).hex()
        username = f"hsmart_{suffix}"
        email = f"hsmart_{suffix}@meikova.io"
        password = "password123"

        reg = auth_manager.register_user(username, password, email=email, display_name="Harvest Smart")
        user_id = reg["id"]

        # 1. By ID
        u1 = auth_manager.find_user_by_identifier(user_id)
        self.assertIsNotNone(u1)
        self.assertEqual(u1["username"], username)

        # 2. By Username
        u2 = auth_manager.find_user_by_identifier(username)
        self.assertIsNotNone(u2)
        self.assertEqual(u2["id"], user_id)

        # 3. By Email
        u3 = auth_manager.find_user_by_identifier(email)
        self.assertIsNotNone(u3)
        self.assertEqual(u3["id"], user_id)

        # 4. By prefix
        prefix = f"hsmart_{suffix}"
        u4 = auth_manager.find_user_by_identifier(prefix)
        self.assertIsNotNone(u4)
        self.assertEqual(u4["id"], user_id)

    def test_02_jit_provisioning_sso(self):
        suffix = os.urandom(4).hex()
        sub = f"gw_harv_{suffix}"
        username = f"sso_harv_{suffix}"
        email = f"sso_harv_{suffix}@meikova.io"

        token = sso_signer.issue_token(
            user_id=sub,
            username=username,
            email=email,
            display_name=f"SSO Harv {suffix}",
            expires_in_sec=86400
        )

        resp = self.client.post("/api/auth/sso/callback", json={"token": token})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["user"]["id"], sub)

        # Verify mirrored in local database
        u = auth_manager.find_user_by_identifier(sub)
        self.assertIsNotNone(u)
        self.assertEqual(u["gateway_user_id"], sub)
        self.assertEqual(u["email"], email)

    def test_03_auth_sync_queue_and_push(self):
        suffix = os.urandom(4).hex()
        username = f"offline_harv_{suffix}"
        email = f"offline_{suffix}@meikova.io"
        password = "password123"

        reg = auth_manager.register_user(username, password, email=email)
        user_id = reg["id"]

        # Check sync status API
        resp = self.client.get("/api/auth/sync/status")
        self.assertEqual(resp.status_code, 200)
        status_data = resp.get_json()
        self.assertTrue(status_data["success"])
        self.assertGreaterEqual(status_data["queue_count"], 1)

        # Push queue
        push_resp = self.client.post("/api/auth/sync/push")
        self.assertEqual(push_resp.status_code, 200)
        push_data = push_resp.get_json()
        self.assertTrue(push_data["success"])
        self.assertGreaterEqual(push_data["synced_count"], 1)

    def test_04_conflict_resolution_same_email(self):
        suffix = os.urandom(4).hex()
        email = f"alice_h_{suffix}@test.io"
        username = f"alice_local_{suffix}"
        password = "password123"

        reg = auth_manager.register_user(username, password, email=email, display_name="Alice Harvest")
        local_id = reg["id"]

        gw_sub = f"gw_alice_h_{suffix}"
        gw_sync_resp = self.client.post("/api/auth/sync/gateway", json={
            "account": {
                "id": gw_sub,
                "email": email,
                "username": f"alice_gw_{suffix}",
                "display_name": "Alice Gateway"
            }
        })
        self.assertEqual(gw_sync_resp.status_code, 200)
        res_data = gw_sync_resp.get_json()
        self.assertTrue(res_data["success"])
        results = res_data["results"]
        self.assertEqual(results[0]["action"], "LINKED")
        self.assertEqual(results[0]["local_id"], local_id)

        # Verify local user record updated with gateway_user_id
        u = auth_manager.find_user_by_identifier(local_id)
        self.assertEqual(u["gateway_user_id"], gw_sub)

    def test_05_conflict_resolution_same_username(self):
        suffix = os.urandom(4).hex()
        username = f"bob_harv_{suffix}"
        local_email = f"bob_local_{suffix}@harvest.io"
        password = "password123"

        reg = auth_manager.register_user(username, password, email=local_email, display_name="Bob Harvest")
        local_id = reg["id"]

        gw_sub = f"gw_bob_h_{suffix}"
        gw_email = f"bob_gw_{suffix}@gateway.io"
        gw_sync_resp = self.client.post("/api/auth/sync/gateway", json={
            "account": {
                "id": gw_sub,
                "email": gw_email,
                "username": username,
                "display_name": "Bob Gateway"
            }
        })
        self.assertEqual(gw_sync_resp.status_code, 200)
        res_data = gw_sync_resp.get_json()
        self.assertTrue(res_data["success"])
        results = res_data["results"]
        self.assertEqual(results[0]["action"], "RESOLVED_NAMESPACE")
        self.assertIn(f"{username}_local_", results[0]["local_renamed_to"])

        # Local user renamed
        old_local = auth_manager.find_user_by_identifier(local_id)
        self.assertEqual(old_local["username"], results[0]["local_renamed_to"])

        # Gateway user now has the canonical username
        gw_user = auth_manager.find_user_by_identifier(gw_sub)
        self.assertEqual(gw_user["username"], username)


if __name__ == "__main__":
    unittest.main()
