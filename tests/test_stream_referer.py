import unittest
from unittest.mock import patch, MagicMock
from app import app

class TestStreamReferer(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    @patch('extractors.generic.fetch_html')
    def test_proxy_sub_dynamic_referer(self, mock_fetch):
        mock_fetch.return_value = '<html><head><script src="/static/avs-shield.min.js"></script></head><body><div id="player"></div></body></html>'
        
        # Test request with custom referer from animevietsub.nl
        response = self.client.get('/api/system/proxy-sub?url=https://storage.googleapiscdn.com/player/test1234&mode=html&referer=https://animevietsub.nl/')
        self.assertEqual(response.status_code, 200)
        
        # Verify fetch_html was called with headers containing Referer = https://animevietsub.nl/
        call_args = mock_fetch.call_args
        self.assertIsNotNone(call_args)
        headers = call_args[1].get('headers', {})
        self.assertEqual(headers.get('Referer'), 'https://animevietsub.nl/')
        self.assertEqual(headers.get('Origin'), 'https://storage.googleapiscdn.com')
        
        # Verify avs-shield.min.js is NOT stripped
        content = response.data.decode('utf-8')
        self.assertIn('avs-shield.min.js', content)
        # Verify MSE chunk hook and auto_stream acceleration are injected
        self.assertIn('_mseAppendHooked', content)
        self.assertIn('MSE_STREAM_COMPLETE', content)

if __name__ == '__main__':
    unittest.main()
