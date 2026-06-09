import unittest
from unittest.mock import patch
import json
import sys
import os

# Set stdout/stderr to UTF-8 to support Vietnamese characters on Windows console
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Ensure project root is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

class TestYoutubeBotDetection(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('yt_dlp.YoutubeDL')
    def test_youtube_bot_challenge_detection(self, mock_ydl_class):
        # Set up mock instance
        mock_instance = mock_ydl_class.return_value
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.extract_info.side_effect = Exception("Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies for the authentication.")
        
        payload = {
            "url": "https://www.youtube.com/watch?v=xubKh9u0uDY",
            "client_id": "test_client_id"
        }
        
        response = self.app.post('/api/info', 
                                 data=json.dumps(payload),
                                 content_type='application/json')
        
        print("\nStatus code (bot challenge):", response.status_code)
        data = json.loads(response.data.decode('utf-8'))
        print("Response data (bot challenge):", data)
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data.get("status"), "error")
        self.assertIn("YouTube yêu cầu xác minh danh tính", data.get("message"))
        self.assertIn("cookie J2TEAM", data.get("message"))

    @patch('yt_dlp.YoutubeDL')
    def test_youtube_private_video_detection(self, mock_ydl_class):
        # Set up mock instance
        mock_instance = mock_ydl_class.return_value
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.extract_info.side_effect = Exception("This is a private video")
        
        payload = {
            "url": "https://www.youtube.com/watch?v=xubKh9u0uDY",
            "client_id": "test_client_id"
        }
        
        response = self.app.post('/api/info', 
                                 data=json.dumps(payload),
                                 content_type='application/json')
        
        print("\nStatus code (private):", response.status_code)
        data = json.loads(response.data.decode('utf-8'))
        print("Response data (private):", data)
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data.get("status"), "error")
        self.assertIn("YouTube yêu cầu xác minh danh tính", data.get("message"))

if __name__ == '__main__':
    unittest.main()
