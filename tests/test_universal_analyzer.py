import unittest
from unittest.mock import patch, MagicMock

from app import app
from extractors.generic import (
    is_direct_media_url,
    extract_direct_media_info,
    generic_html_link_harvester
)

class TestUniversalAnalyzer(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

    def test_is_direct_media_url(self):
        """Test is_direct_media_url accurately detects direct stream files"""
        self.assertTrue(is_direct_media_url("https://cdn.example.com/live/master.m3u8"))
        self.assertTrue(is_direct_media_url("https://cdn.example.com/manifest.mpd"))
        self.assertTrue(is_direct_media_url("https://storage.cdn.net/movies/sample.mp4?token=123"))
        self.assertTrue(is_direct_media_url("https://podcasts.example.com/episodes/show.mp3"))
        self.assertTrue(is_direct_media_url("https://archive.org/audio/track.flac"))
        self.assertTrue(is_direct_media_url("https://cdn.site.com/get?file=video.mp4&user=1"))
        self.assertFalse(is_direct_media_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertFalse(is_direct_media_url("https://vnexpress.net/tin-tuc-thoi-su"))
        self.assertFalse(is_direct_media_url("data:image/png;base64,1234"))

    def test_extract_direct_media_info_mp4(self):
        """Test extract_direct_media_info immediately extracts progressive MP4 metadata"""
        with patch('extractors.generic.get_url_content_length', return_value=104857600): # 100MB
            res = extract_direct_media_info("https://media.server.org/downloads/sample_movie.mp4")
            self.assertIsNotNone(res)
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["title"], "sample movie")
            self.assertTrue(len(res["video_options"]) > 0)
            opt = res["video_options"][0]
            self.assertEqual(opt["ext"], "mp4")
            self.assertEqual(opt["type"], "video")
            self.assertEqual(opt["size"], "100.0 MB")

    def test_extract_direct_media_info_audio(self):
        """Test extract_direct_media_info classifies audio into audio_options"""
        with patch('extractors.generic.get_url_content_length', return_value=15728640): # 15MB
            res = extract_direct_media_info("https://podcast.server.fm/episodes/deep_dive.mp3")
            self.assertIsNotNone(res)
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["category"], "Audio")
            self.assertTrue(len(res["audio_options"]) > 0)
            a_opt = res["audio_options"][0]
            self.assertEqual(a_opt["ext"], "mp3")
            self.assertEqual(a_opt["type"], "audio")
            self.assertEqual(a_opt["size"], "15.0 MB")

    def test_extract_direct_media_info_hls_master_variants(self):
        """Test extract_direct_media_info expands HLS master playlist into resolution tiers"""
        master_m3u8 = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1920x1080
1080p/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2500000,RESOLUTION=1280x720
720p/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=854x480
480p/index.m3u8
"""
        with patch('curl_cffi.requests.get') as mock_curl:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = master_m3u8
            mock_curl.return_value = mock_resp

            res = extract_direct_media_info("https://stream.server.net/vod/master.m3u8")
            self.assertIsNotNone(res)
            self.assertEqual(res["status"], "success")
            self.assertEqual(len(res["video_options"]), 3)
            res_labels = [opt["resolution"] for opt in res["video_options"]]
            self.assertIn("1080p", res_labels)
            self.assertIn("720p", res_labels)
            self.assertIn("480p", res_labels)

    def test_generic_harvester_schema_org_json_ld(self):
        """Test generic_html_link_harvester extracts Schema.org VideoObject and AudioObject"""
        html = '''
        <html>
        <head>
            <title>Cooking Masterclass</title>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "VideoObject",
                "name": "How to cook Wagyu steak",
                "contentUrl": "https://cdn.recipes.com/videos/wagyu_master.m3u8"
            }
            </script>
            <script type="application/ld+json">
            {
                "@type": "AudioObject",
                "name": "Audio commentary",
                "contentUrl": "https://cdn.recipes.com/audio/commentary.mp3"
            }
            </script>
        </head>
        <body><p>Article content</p></body>
        </html>
        '''
        res = generic_html_link_harvester("https://recipes.com/guide/wagyu", None, html=html)
        self.assertIsNotNone(res)
        video_opts = res.get("video_options", [])
        audio_opts = res.get("audio_options", [])
        
        self.assertTrue(any("wagyu_master.m3u8" in opt["url"] for opt in video_opts))
        self.assertTrue(any("commentary.mp3" in opt["url"] for opt in audio_opts))

    def test_generic_harvester_opengraph_media(self):
        """Test generic_html_link_harvester extracts og:video and og:audio meta tags"""
        html = '''
        <html>
        <head>
            <title>News Report Video</title>
            <meta property="og:video" content="https://video.newsportal.com/reports/2026/breaking.mp4" />
            <meta property="og:audio" content="https://radio.newsportal.com/podcasts/news_daily.mp3" />
        </head>
        <body><main>Content</main></body>
        </html>
        '''
        res = generic_html_link_harvester("https://newsportal.com/breaking-story", None, html=html)
        self.assertIsNotNone(res)
        self.assertTrue(any("breaking.mp4" in opt["url"] for opt in res.get("video_options", [])))
        self.assertTrue(any("news_daily.mp3" in opt["url"] for opt in res.get("audio_options", [])))

    def test_generic_harvester_html5_audio_tags(self):
        """Test generic_html_link_harvester extracts HTML5 <audio> sources into audio_options"""
        html = '''
        <html>
        <head><title>Music Blog</title></head>
        <body>
            <audio controls>
                <source src="/media/audio/track01.mp3" type="audio/mpeg">
                <source src="/media/audio/track01.ogg" type="audio/ogg">
            </audio>
        </body>
        </html>
        '''
        res = generic_html_link_harvester("https://musicblog.org/album/review", None, html=html)
        self.assertIsNotNone(res)
        audio_opts = res.get("audio_options", [])
        self.assertTrue(len(audio_opts) > 0)
        self.assertTrue(any("track01.mp3" in opt["url"] for opt in audio_opts))
        self.assertEqual(res.get("category"), "Web Audio")

    def test_generic_harvester_nextjs_payload(self):
        """Test generic_html_link_harvester extracts streams embedded in Next.js __NEXT_DATA__"""
        html = '''
        <html>
        <head><title>Next.js Streaming Portal</title></head>
        <body>
            <script id="__NEXT_DATA__" type="application/json">
            {
                "props": {
                    "pageProps": {
                        "videoSource": "https://cdn.nextportal.io/streams/film_master.m3u8?auth=token99"
                    }
                }
            }
            </script>
        </body>
        </html>
        '''
        res = generic_html_link_harvester("https://nextportal.io/watch/film", None, html=html)
        self.assertIsNotNone(res)
        video_opts = res.get("video_options", [])
        self.assertTrue(any("film_master.m3u8" in opt["url"] for opt in video_opts))

    def test_generic_harvester_universal_player_config(self):
        """Test generic_html_link_harvester extracts streams from JWPlayer / Video.js JS setups"""
        html = '''
        <html>
        <head><title>Independent Cinema</title></head>
        <body>
            <div id="player"></div>
            <script>
                jwplayer("player").setup({
                    file: "https://vod.indiecinema.org/hls/master_presentation.m3u8",
                    width: "100%"
                });
            </script>
        </body>
        </html>
        '''
        res = generic_html_link_harvester("https://indiecinema.org/film/festival", None, html=html)
        self.assertIsNotNone(res)
        video_opts = res.get("video_options", [])
        self.assertTrue(any("master_presentation.m3u8" in opt["url"] for opt in video_opts))

    def test_api_info_endpoint_direct_media_fast_path(self):
        """Test /api/info fast-paths direct media URLs without invoking yt-dlp"""
        with patch('extractors.generic.get_url_content_length', return_value=52428800):
            resp = self.client.post('/api/info', json={
                "url": "https://cdn.example.com/media/instant_video.mp4"
            })
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertEqual(data.get("status"), "success")
            self.assertEqual(data.get("platform_class"), "direct")
            self.assertEqual(data.get("title"), "instant video")
            self.assertTrue(len(data.get("video_options", [])) > 0)


if __name__ == '__main__':
    unittest.main()
