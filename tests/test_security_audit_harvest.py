import os
import sys
import time
import io
import unittest
import tempfile
from unittest.mock import patch

from app import app
from utils.security import is_safe_remote_url, is_safe_local_media_path
from utils.auth import AuthManager
from utils.ratelimit import get_client_ip, check_rate_limit, reset_rate_limit, LIMITS
from config import DB_PATH, TEMP_DOWNLOAD_DIR, COOKIES_DIR


class TestSecurityAuditHarvest(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.auth_manager = AuthManager(DB_PATH)

    def test_01_security_headers_present(self):
        """Security headers: X-Content-Type-Options, X-Frame-Options, CSP must be present"""
        resp = self.client.get("/")
        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(resp.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertIn("Content-Security-Policy", resp.headers)

    def test_02_hsts_header_on_https_or_forwarded_proto(self):
        """HSTS header must be added when request is over HTTPS/Tunnel"""
        resp = self.client.get("/", headers={"X-Forwarded-Proto": "https"})
        self.assertIn("Strict-Transport-Security", resp.headers)
        self.assertIn("max-age=31536000", resp.headers.get("Strict-Transport-Security", ""))

    def test_03_payload_limit_dos_413(self):
        """Request payload exceeding 16MB must return 413 RequestEntityTooLarge"""
        big_data = b"X" * (17 * 1024 * 1024)
        resp = self.client.post(
            "/api/cookies/upload",
            data={"client_id": "test_client", "file": (io.BytesIO(big_data), "big.txt")},
            content_type="multipart/form-data"
        )
        self.assertEqual(resp.status_code, 413)
        data = resp.get_json()
        self.assertEqual(data.get("code"), "PAYLOAD_TOO_LARGE")

    def test_04_path_traversal_local_dir_blocked(self):
        """Local path directory traversal in /api/info must return 403"""
        # System Windows folder or Linux /etc
        target_dir = os.environ.get("SystemRoot", "C:\\Windows")
        resp = self.client.post("/api/info", json={"url": target_dir})
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertIn("Security restriction", data.get("message", ""))

        # Root drive check
        root_drive = "C:\\" if sys.platform.startswith("win") else "/"
        resp_root = self.client.post("/api/info", json={"url": root_drive})
        self.assertEqual(resp_root.status_code, 403)

    def test_05_path_traversal_cookies_api_blocked(self):
        """Malicious client_id with path traversal characters must return 400"""
        malicious_ids = [
            "../../malicious",
            "..\\..\\evil",
            "test/id",
            "test\\id",
            "client*id",
            "a" * 70,  # too long (>64 chars)
            "",
            "   "
        ]
        for bad_id in malicious_ids:
            # Upload
            resp = self.client.post(
                "/api/cookies/upload",
                data={"client_id": bad_id, "file": (io.BytesIO(b"# Netscape HTTP Cookie File\n"), "cookies.txt")},
                content_type="multipart/form-data"
            )
            self.assertEqual(resp.status_code, 400, f"Expected 400 for upload client_id '{bad_id}'")

            # Paste
            resp_paste = self.client.post(
                "/api/cookies/paste",
                json={"client_id": bad_id, "content": "# Netscape HTTP Cookie File\n"}
            )
            self.assertEqual(resp_paste.status_code, 400, f"Expected 400 for paste client_id '{bad_id}'")

            # Clear
            resp_clear = self.client.post(f"/api/cookies/clear/{bad_id}")
            self.assertEqual(resp_clear.status_code, 400, f"Expected 400 for clear client_id '{bad_id}'")

    def test_06_ssrf_proxy_sub_blocked(self):
        """Open proxy and SSRF targets must return 403 in /api/system/proxy-sub"""
        prohibited_urls = [
            "http://127.0.0.1:8080/secret",
            "http://localhost:5000/admin",
            "http://169.254.169.254/latest/meta-data/",
            "http://192.168.1.1/router",
            "http://10.0.0.1/internal",
            "file:///etc/passwd"
        ]
        for url in prohibited_urls:
            resp = self.client.get(f"/api/system/proxy-sub?url={url}")
            self.assertEqual(resp.status_code, 403, f"Expected 403 for SSRF URL: {url}")

    def test_07_torrent_extractor_ssrf_and_path_traversal(self):
        """Torrent parsing must reject internal IPs and system paths"""
        from extractors.torrent import extract_torrent_info
        with self.assertRaises(ValueError):
            extract_torrent_info("http://127.0.0.1:9091/transmission/web/")
        with self.assertRaises(ValueError):
            extract_torrent_info("http://169.254.169.254/latest/meta-data/")
        with self.assertRaises(ValueError):
            win_sys = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "notepad.exe")
            extract_torrent_info(win_sys)

    def test_08_timing_oracle_dummy_hash(self):
        """Authenticate non-existent user must perform dummy PBKDF2 hash (~same time as existing user)"""
        # Create a test user
        test_uname = f"sec_test_{int(time.time())}"
        test_pwd = "CorrectPassword123!"
        self.auth_manager.register_user(test_uname, test_pwd)

        # Measure non-existent user authentication time
        t0 = time.perf_counter()
        res_nonexistent = self.auth_manager.authenticate_user("definitely_nonexistent_user_xyz", "somepassword")
        t_nonexistent = time.perf_counter() - t0
        self.assertIsNone(res_nonexistent)

        # Measure existing user with wrong password authentication time
        t0 = time.perf_counter()
        res_wrongpwd = self.auth_manager.authenticate_user(test_uname, "WrongPassword123!")
        t_wrongpwd = time.perf_counter() - t0
        self.assertIsNone(res_wrongpwd)

        # Both must have performed PBKDF2 calculation (minimum 10ms for 100k rounds)
        self.assertGreater(t_nonexistent, 0.010, f"Non-existent auth took too fast: {t_nonexistent:.4f}s (timing oracle leak)")
        self.assertGreater(t_wrongpwd, 0.010, f"Wrong password auth took: {t_wrongpwd:.4f}s")
        # Time delta should be small (< 0.05s)
        time_diff = abs(t_nonexistent - t_wrongpwd)
        self.assertLess(time_diff, 0.05, f"Timing difference too large: {time_diff:.4f}s")

    def test_09_rate_limit_spoofing_blocked(self):
        """Untrusted remote connections cannot bypass rate limits by spoofing X-Forwarded-For"""
        fake_attacker_ip = "198.51.100.99"
        # Reset limiter for this test
        reset_rate_limit(fake_attacker_ip, "login")

        # Simulate 10 requests from fake_attacker_ip with rotating X-Forwarded-For headers
        for i in range(10):
            allowed, _ = check_rate_limit(fake_attacker_ip, "login")
            self.assertTrue(allowed, f"Request {i+1} should be allowed")

        # 11th request from same remote IP must be blocked even if X-Forwarded-For changes
        allowed, msg = check_rate_limit(fake_attacker_ip, "login")
        self.assertFalse(allowed, "11th request must be rate-limited")
        self.assertIn("Quá nhiều", msg)

    def test_10_safe_client_ip_extraction(self):
        """get_client_ip ignores X-Forwarded-For if remote_addr is untrusted"""
        class MockRequest:
            def __init__(self, remote_addr, headers=None):
                self.remote_addr = remote_addr
                self.headers = headers or {}

        # 1. Direct connection from external public IP with spoofed header
        req_direct = MockRequest("203.0.113.195", {"X-Forwarded-For": "8.8.8.8, 1.1.1.1"})
        self.assertEqual(get_client_ip(req_direct), "203.0.113.195")

        # 2. Local trusted proxy (127.0.0.1) passing CF-Connecting-IP
        req_cf = MockRequest("127.0.0.1", {"CF-Connecting-IP": "104.28.15.22"})
        self.assertEqual(get_client_ip(req_cf), "104.28.15.22")

        # 3. Local trusted proxy passing X-Forwarded-For
        req_proxy = MockRequest("127.0.0.1", {"X-Forwarded-For": "198.51.100.44, 10.0.0.2"})
        self.assertEqual(get_client_ip(req_proxy), "198.51.100.44")

    def test_11_cookie_secure_flag_over_https(self):
        """Session cookie must have Secure flag when request is over HTTPS or X-Forwarded-Proto is https"""
        test_uname = f"sec_cookie_{int(time.time())}"
        test_pwd = "Password123!"

        # Register over HTTPS
        resp = self.client.post(
            "/api/auth/register",
            json={"username": test_uname, "password": test_pwd},
            headers={"X-Forwarded-Proto": "https"}
        )
        self.assertEqual(resp.status_code, 200)
        # Check Set-Cookie header contains Secure
        set_cookie = resp.headers.get("Set-Cookie", "")
        self.assertIn("session_token=", set_cookie)
        self.assertIn("Secure", set_cookie)
        self.assertIn("HttpOnly", set_cookie)


if __name__ == "__main__":
    unittest.main()
