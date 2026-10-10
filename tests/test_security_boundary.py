import os
import sys
import unittest
import tempfile
from unittest.mock import patch, MagicMock

from app import app
from utils.security import is_safe_remote_url, is_safe_local_media_path
from config import TEMP_DOWNLOAD_DIR

class TestSecurityBoundary(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

    def test_ssrf_rejects_loopback_and_private_ips(self):
        """Test is_safe_remote_url blocks loopback, private ranges and cloud metadata"""
        # Loopback
        safe, _ = is_safe_remote_url("http://127.0.0.1:5000/api/info")
        self.assertFalse(safe)

        safe, _ = is_safe_remote_url("http://localhost:8080/status")
        self.assertFalse(safe)

        safe, _ = is_safe_remote_url("http://0.0.0.0:3000/")
        self.assertFalse(safe)

        # Private Class A, B, C
        safe, _ = is_safe_remote_url("http://10.0.0.1/admin")
        self.assertFalse(safe)

        safe, _ = is_safe_remote_url("https://172.16.0.5:8443/console")
        self.assertFalse(safe)

        safe, _ = is_safe_remote_url("http://192.168.1.1/router")
        self.assertFalse(safe)

        # Cloud metadata
        safe, _ = is_safe_remote_url("http://169.254.169.254/latest/meta-data")
        self.assertFalse(safe)

        # Scheme check
        safe, _ = is_safe_remote_url("file:///etc/passwd")
        self.assertFalse(safe)

        safe, _ = is_safe_remote_url("ftp://server.local/file")
        self.assertFalse(safe)

    def test_ssrf_allows_public_urls(self):
        """Test is_safe_remote_url permits genuine public web addresses"""
        safe, _ = is_safe_remote_url("https://example.com/video.mp4")
        self.assertTrue(safe)

        safe, _ = is_safe_remote_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertTrue(safe)

    def test_path_jail_blocks_executables(self):
        """Test is_safe_local_media_path blocks executable extensions"""
        for bad_ext in [".exe", ".bat", ".cmd", ".ps1", ".vbs", ".msi", ".reg"]:
            fake_path = os.path.join(TEMP_DOWNLOAD_DIR, f"payload{bad_ext}")
            safe, reason = is_safe_local_media_path(fake_path, allow_user_local_media=True)
            self.assertFalse(safe)
            self.assertIn("prohibited", reason.lower())

    def test_path_jail_blocks_system_directories(self):
        """Test is_safe_local_media_path blocks sensitive system OS directories"""
        win_sys = "C:\\Windows\\System32\\drivers\\etc\\hosts"
        safe, reason = is_safe_local_media_path(win_sys, allow_user_local_media=True)
        self.assertFalse(safe)

    def test_path_jail_allows_safe_temp_media(self):
        """Test is_safe_local_media_path permits media inside temporary or user download dirs"""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            tmp.write(b'video-data')
            tmp_path = tmp.name

        try:
            safe, _ = is_safe_local_media_path(tmp_path, allow_user_local_media=False)
            self.assertTrue(safe)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_open_file_endpoint_rejects_executable(self):
        """Test /api/download/open-file returns 403 when requesting an executable"""
        with tempfile.NamedTemporaryFile(suffix='.exe', delete=False) as tmp:
            tmp.write(b'MZ-dummy-binary')
            tmp_path = tmp.name

        try:
            resp = self.client.post('/api/download/open-file', json={'file_path': tmp_path})
            self.assertEqual(resp.status_code, 403)
            data = resp.get_json()
            self.assertIn("Security restriction", data.get("message", ""))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_proxy_stream_endpoint_blocks_ssrf(self):
        """Test /api/proxy/stream returns 403 on internal IP target"""
        resp = self.client.get('/api/proxy/stream?url=http://127.0.0.1:8080/internal')
        self.assertEqual(resp.status_code, 403)
        self.assertIn(b"Security restriction", resp.data)

        resp2 = self.client.get('/api/proxy/stream?url=http://169.254.169.254/latest/meta-data')
        self.assertEqual(resp2.status_code, 403)
        self.assertIn(b"Security restriction", resp2.data)

    def test_download_image_endpoint_blocks_ssrf(self):
        """Test /api/download/image returns 403 on internal IP target"""
        resp = self.client.get('/api/download/image?url=http://192.168.1.1/admin.png')
        self.assertEqual(resp.status_code, 403)
        self.assertIn(b"Security restriction", resp.data)

    def test_proxy_sub_endpoint_blocks_ssrf(self):
        """Test /api/system/proxy-sub returns 403 on loopback address"""
        resp = self.client.get('/api/system/proxy-sub?url=http://localhost:5000/sub.vtt')
        self.assertEqual(resp.status_code, 403)
        self.assertIn(b"Security restriction", resp.data)

    def test_convert_endpoints_reject_dangerous_files(self):
        """Test converter endpoints reject executable paths with 403"""
        with tempfile.NamedTemporaryFile(suffix='.bat', delete=False) as tmp:
            tmp.write(b'@echo off')
            tmp_path = tmp.name

        try:
            resp = self.client.post('/api/convert/probe', json={'file_path': tmp_path})
            self.assertEqual(resp.status_code, 403)

            resp2 = self.client.get(f'/api/convert/preview-stream?file_path={tmp_path}')
            self.assertEqual(resp2.status_code, 403)

            resp3 = self.client.post('/api/convert', json={'file_path': tmp_path, 'target_format': 'mp3'})
            self.assertEqual(resp3.status_code, 403)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == '__main__':
    unittest.main()
