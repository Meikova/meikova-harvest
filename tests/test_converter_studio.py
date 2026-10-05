import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from app import app
from tasks.convert import probe_media_file, start_conversion_task
from config import TEMP_DOWNLOAD_DIR, downloads_status

class TestConverterStudio(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_probe_endpoint_missing_file(self):
        """Test probe endpoint returns 404 for missing file"""
        resp = self.client.post("/api/convert/probe", json={"file_path": "/non/existent/path.mp4"})
        self.assertEqual(resp.status_code, 404)

    def test_probe_endpoint_valid_mock(self):
        """Test probe endpoint parses metadata correctly"""
        dummy_file = os.path.join(self.temp_dir, "test.mp4")
        with open(dummy_file, "wb") as f:
            f.write(b"dummy mp4 content")

        mock_probe = {
            "duration": 45.2,
            "width": 1920,
            "height": 1080,
            "video_codec": "h264",
            "audio_codec": "aac",
            "channels": 2,
            "sample_rate": 48000,
            "bitrate": 2500000,
            "size": len(b"dummy mp4 content"),
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2"
        }

        with patch("routes.convert.probe_media_file", return_value=mock_probe):
            resp = self.client.post("/api/convert/probe", json={"file_path": dummy_file})
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["probe"]["duration"], 45.2)
            self.assertEqual(data["probe"]["video_codec"], "h264")

    def test_preview_stream_endpoint(self):
        """Test /api/convert/preview-stream returns range-capable media file"""
        dummy_file = os.path.join(self.temp_dir, "preview_test.mp3")
        with open(dummy_file, "wb") as f:
            f.write(b"ID3" + b"\x00" * 100)

        resp = self.client.get(f"/api/convert/preview-stream?file_path={dummy_file}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("Content-Type"), "audio/mpeg")

    def test_preview_stream_missing(self):
        """Test /api/convert/preview-stream returns 404 for missing file"""
        resp = self.client.get("/api/convert/preview-stream?file_path=/fake/missing.mp4")
        self.assertEqual(resp.status_code, 404)

    def test_trigger_conversion_endpoint(self):
        """Test /api/convert initiates task in downloads_status"""
        dummy_file = os.path.join(self.temp_dir, "video.mp4")
        with open(dummy_file, "wb") as f:
            f.write(b"data")

        with patch("routes.convert.start_conversion_task") as mock_start:
            resp = self.client.post("/api/convert", json={
                "file_path": dummy_file,
                "filename": "video.mp4",
                "target_format": "mp3",
                "audio_bitrate": "320k"
            })
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertEqual(data["status"], "success")
            self.assertTrue(data["download_id"].startswith("convert-"))
            self.assertEqual(data["filename"], "video.mp3")
            mock_start.assert_called_once()

    def test_safety_guard_user_file_retention(self):
        """Critical safety check: user files outside UPLOAD_DIR must NEVER be deleted after conversion"""
        user_local_file = os.path.join(self.temp_dir, "original_user_movie.mp4")
        with open(user_local_file, "wb") as f:
            f.write(b"irreplaceable user home movie data")

        self.assertTrue(os.path.exists(user_local_file))

        # Simulate conversion task running on user local file
        task_id = "test-safety-guard"
        downloads_status[task_id] = {
            "status": "pending",
            "progress": 0,
            "message": "Starting...",
            "filepath": ""
        }

        # Mock ffmpeg execution to succeed
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = (b"", b"")
            mock_proc.poll.return_value = 0
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            from tasks.convert import run_conversion
            run_conversion(task_id, user_local_file, "original_user_movie.mp4", "mp3", {})

        # Assert user original file is STILL on disk and NOT deleted!
        self.assertTrue(os.path.exists(user_local_file), "CRITICAL BUG: User original local file was deleted by converter!")


if __name__ == "__main__":
    unittest.main()
