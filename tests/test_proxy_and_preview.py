import unittest
from unittest.mock import patch, MagicMock
from app import app

class TestProxyAndPreview(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

    def test_proxy_stream_missing_url(self):
        resp = self.client.get('/api/proxy/stream')
        self.assertEqual(resp.status_code, 400)

    def test_proxy_stream_audio_content_type(self):
        """Test that proxy_stream correctly detects audio Content-Type instead of hardcoded video/mp4"""
        with patch('curl_cffi.requests.get') as mock_curl:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {'Content-Type': 'audio/mpeg'}
            mock_resp.iter_content.return_value = iter([b'fake-mp3-bytes'])
            mock_curl.return_value = mock_resp

            resp = self.client.get('/api/proxy/stream?url=https://example.com/audio.mp3')
            self.assertEqual(resp.status_code, 200)
            self.assertIn('audio/mpeg', resp.headers.get('Content-Type', ''))

    def test_proxy_stream_audio_url_fallback_mime(self):
        """Test that proxy_stream derives audio/mpeg from .mp3 url when upstream returns no Content-Type"""
        with patch('curl_cffi.requests.get') as mock_curl:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {}
            mock_resp.iter_content.return_value = iter([b'fake-mp3-bytes'])
            mock_curl.return_value = mock_resp

            resp = self.client.get('/api/proxy/stream?url=https://example.com/track.mp3')
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.headers.get('Content-Type'), 'audio/mpeg')

    def test_proxy_stream_curl_fallback_to_requests(self):
        """Test that when curl_cffi raises an exception (e.g. DNS failure), it falls back to requests with DoH"""
        with patch('curl_cffi.requests.get') as mock_curl, \
             patch('requests.get') as mock_req:
            mock_curl.side_effect = Exception("curl connection failed")
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {'Content-Type': 'audio/mpeg'}
            mock_resp.iter_content.return_value = iter([b'req-audio-bytes'])
            mock_req.return_value = mock_resp

            resp = self.client.get('/api/proxy/stream?url=https://example.com/fallback.mp3')
            self.assertEqual(resp.status_code, 200)
            mock_req.assert_called_once()

    def test_stream_adaptive_video_only(self):
        """Test that stream_adaptive works when audio_url is empty (video-only adaptive stream)"""
        with patch('subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.stdout.read.side_effect = [b'video-chunk', b'']
            mock_popen.return_value = mock_proc

            resp = self.client.get('/api/proxy/stream_adaptive?video_url=https://example.com/video.mp4&audio_url=')
            self.assertEqual(resp.status_code, 200)
    def test_proxy_stream_partial_content_range_headers(self):
        """Test that proxy_stream forwards 206 Partial Content, Content-Range, and Content-Length intact"""
        with patch('curl_cffi.requests.get') as mock_curl:
            mock_resp = MagicMock()
            mock_resp.status_code = 206
            mock_resp.headers = {
                'Content-Type': 'video/mp4',
                'Content-Range': 'bytes 0-1023/2048',
                'Content-Length': '1024',
                'Accept-Ranges': 'bytes'
            }
            mock_resp.iter_content.return_value = iter([b'x' * 1024])
            mock_curl.return_value = mock_resp

            resp = self.client.get(
                '/api/proxy/stream?url=https://example.com/video.mp4',
                headers={'Range': 'bytes=0-1023'}
            )
            self.assertEqual(resp.status_code, 206)
            self.assertEqual(resp.headers.get('Content-Range'), 'bytes 0-1023/2048')
            self.assertEqual(resp.headers.get('Content-Length'), '1024')
            self.assertEqual(resp.headers.get('Accept-Ranges'), 'bytes')

    def test_proxy_image_403_fallback_svg(self):
        """Test that proxy_image returns SVG placeholder when upstream returns 403 Forbidden (e.g. expired CDN token)"""
        with patch('requests.get') as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 403
            mock_resp.content = b"URL signature expired"
            mock_req.return_value = mock_resp

            resp = self.client.get('/api/proxy/image?url=https://scontent.xx.fbcdn.net/expired.jpg')
            self.assertEqual(resp.status_code, 200)
            self.assertIn('image/svg+xml', resp.headers.get('Content-Type', ''))
            self.assertIn(b'<svg', resp.data)

    def test_proxy_image_success(self):
        """Test that proxy_image returns image content when upstream returns 200"""
        with patch('requests.get') as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {'Content-Type': 'image/jpeg'}
            mock_resp.content = b'\xff\xd8\xff\xe0test-jpg'
            mock_req.return_value = mock_resp

            resp = self.client.get('/api/proxy/image?url=https://example.com/image.jpg')
            self.assertEqual(resp.status_code, 200)
            self.assertIn('image/jpeg', resp.headers.get('Content-Type', ''))
            self.assertEqual(resp.data, b'\xff\xd8\xff\xe0test-jpg')

    def test_proxy_subtitle_local_file(self):
        """Test that proxy_subtitle_endpoint serves local disk files correctly (e.g. torrent content files)"""
        import tempfile, os
        with tempfile.NamedTemporaryFile('w', delete=False, suffix='.txt') as tf:
            tf.write("Sample local subtitle/code content")
            temp_path = tf.name

        try:
            resp = self.client.get(f'/api/system/proxy-sub?url={temp_path}&mode=text')
            self.assertEqual(resp.status_code, 200)
            self.assertIn(b"Sample local subtitle/code content", resp.data)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_should_bypass_ytdl_streaming_sites(self):
        """Test that should_bypass_ytdl routes movie/streaming sites to generic harvester and skips social sites"""
        from routes.info import should_bypass_ytdl
        self.assertTrue(should_bypass_ytdl('https://www.rophim.soy/xem-phim/tro-tan-vung-len.yMNadpz3?ver=1'))
        self.assertTrue(should_bypass_ytdl('https://luphim.com/xem-phim/spider-man-brand-new-day-20562/?sv2=true'))
        self.assertTrue(should_bypass_ytdl('https://animevietsub.nl/phim/mushoku-tensei-iii-a5983/tap-14-115941.html'))
        self.assertTrue(should_bypass_ytdl('https://motphim.net/xem-phim/test-movie.html'))
        self.assertFalse(should_bypass_ytdl('https://www.youtube.com/watch?v=dQw4w9WgXcQ'))
        self.assertFalse(should_bypass_ytdl('https://www.facebook.com/watch/?v=123456'))
        self.assertFalse(should_bypass_ytdl('https://www.tiktok.com/@user/video/123456'))

    def test_downloads_count_badge_css(self):
        """Test that styles.css defines downloads count badge with var(--cyan) and light theme styles"""
        import os
        css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'css', 'styles.css')
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        self.assertNotIn('var(--cyan-gradient)', css_content, "--cyan-gradient must not be used as it is undefined")
        self.assertIn('.downloads-count-badge', css_content)
        self.assertIn('.light-theme .downloads-manager', css_content)
        self.assertIn('.light-theme .downloads-count-badge', css_content)

if __name__ == '__main__':
    unittest.main()

