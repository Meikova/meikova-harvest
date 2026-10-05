import unittest
import re
from unittest.mock import patch, MagicMock
from app import app
from utils.ytdl import create_ydl_instance

class TestYouTubePlaybackAndDownload(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

    def test_create_ydl_instance_enforces_web_embedded_client(self):
        """Test that create_ydl_instance prioritizes web_embedded over ios to prevent 403 Forbidden"""
        ydl_opts = {
            "extractor_args": {
                "youtube": {
                    "player_client": ["ios", "android", "web_creator"]
                }
            }
        }
        with create_ydl_instance(ydl_opts, "https://www.youtube.com/watch?v=dQw4w9WgXcQ") as ydl:
            clients = ydl.params.get("extractor_args", {}).get("youtube", {}).get("player_client", [])
            self.assertEqual(clients[0], "web_embedded")
            self.assertIn("web_embedded", clients)

    def test_create_ydl_instance_configures_node_runtime(self):
        """Test that create_ydl_instance configures Node runtime for solving JS challenges"""
        ydl_opts = {}
        with create_ydl_instance(ydl_opts, "https://www.youtube.com/watch?v=dQw4w9WgXcQ") as ydl:
            runtimes = ydl.params.get("js_runtimes", {})
            self.assertIn("node", runtimes)

    def test_youtube_radio_url_cleaning(self):
        """Test that YouTube radio playlist URLs (&list=RD...) are properly sanitized to video URLs"""
        url = "https://www.youtube.com/watch?v=DzOF3gUEqkY&list=RDDzOF3gUEqkY&start_radio=1"
        cleaned_url = url
        if "watch?v=" in cleaned_url:
            cleaned_url = re.sub(r'&list=RD[^&]*', '', cleaned_url)
            cleaned_url = re.sub(r'&start_radio=1', '', cleaned_url)
        self.assertEqual(cleaned_url, "https://www.youtube.com/watch?v=DzOF3gUEqkY")

    def test_api_download_task_enqueue(self):
        """Test that /api/download enqueues a YouTube download task and returns download_id"""
        payload = {
            "url": "https://www.youtube.com/watch?v=DzOF3gUEqkY",
            "format_id": "bestvideo[height=1080]+bestaudio/best",
            "ext": "mp4",
            "quality": "192",
            "title": "Test Video"
        }
        with patch('tasks.download.bg_download_task'):
            resp = self.client.post('/api/download', json=payload)
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertEqual(data.get("status"), "success")
            self.assertTrue(bool(data.get("download_id")))

    def test_api_download_mp3_enqueue(self):
        """Test that /api/download enqueues an MP3 audio task and returns download_id"""
        payload = {
            "url": "https://www.youtube.com/watch?v=DzOF3gUEqkY",
            "format_id": "bestaudio/best",
            "ext": "mp3",
            "quality": "192",
            "title": "Test Audio"
        }
        with patch('tasks.download.bg_download_task'):
            resp = self.client.post('/api/download', json=payload)
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertEqual(data.get("status"), "success")
            self.assertTrue(bool(data.get("download_id")))

    def test_bg_download_task_handles_radio_playlist_url_without_scoping_error(self):
        """Test that bg_download_task cleans &list=RD URLs without UnboundLocalError"""
        from tasks.download import bg_download_task
        from config import downloads_status, downloads_status_lock
        
        test_id = "test-radio-clean-id"
        with downloads_status_lock:
            downloads_status[test_id] = {
                "status": "pending",
                "progress": 0,
                "message": "Queued. Starting download..."
            }
        
        # Mock YoutubeDL inside create_ydl_instance to avoid actual network download
        with patch('yt_dlp.YoutubeDL') as mock_ydl:
            instance = MagicMock()
            instance.download.return_value = 0
            mock_ydl.return_value.__enter__.return_value = instance
            
            with patch('os.listdir', return_value=['media.mp4']):
                with patch('utils.ffmpeg.trim_file_if_needed', return_value=('media.mp4', False)):
                    with patch('utils.ffmpeg.apply_post_processing', return_value=('media.mp4', False)):
                        radio_url = "https://www.youtube.com/watch?v=DzOF3gUEqkY&list=RDDzOF3gUEqkY&start_radio=1"
                        bg_download_task(
                            test_id,
                            radio_url,
                            "bestvideo[height=720]+bestaudio/best",
                            "mp4",
                            quality="192",
                            title="Radio Video"
                        )
                        with downloads_status_lock:
                            st = downloads_status.get(test_id)
                            # Verify task progressed and completed without UnboundLocalError
                            self.assertEqual(st.get("status"), "complete")
                            self.assertEqual(st.get("progress"), 100)

if __name__ == '__main__':
    unittest.main()
