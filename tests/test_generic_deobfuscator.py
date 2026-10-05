import unittest
from extractors.generic import unpack_dean_edwards, deobfuscate_script, scan_text_for_media_urls

class TestGenericDeobfuscator(unittest.TestCase):
    def test_unpack_dean_edwards(self):
        packed = "eval(function(p,a,c,k,e,d){return p}(\"0 1='2://3.4/5.6';\",7,7,'var|videoUrl|https|cdn|example|stream|m3u8'.split('|'),0,{}))"
        unpacked = unpack_dean_edwards(packed)
        self.assertIn("https://cdn.example/stream.m3u8", unpacked)

    def test_deobfuscate_script_hex_and_unicode(self):
        script = r"var stream = '\x68\x74\x74\x70\x73\x3a\x2f\x2f\x65\x78\x61\x6d\x70\x6c\x65\x2e\x63\x6f\x6d\x2f\x76\x69\x64\x65\x6f\x2e\x6d\x70\x34';"
        deobf = deobfuscate_script(script)
        self.assertIn("https://example.com/video.mp4", deobf)

        script_unicode = r"var link = 'https:\u002f\u002fcdn.net\u002fmaster.m3u8';"
        deobf_u = deobfuscate_script(script_unicode)
        self.assertIn("https://cdn.net/master.m3u8", deobf_u)

    def test_scan_text_for_media_urls(self):
        text = '''
        const config = {
            file: "https://streaming.service.com/hls/live.m3u8?token=abc123xyz",
            source: "https://backup.service.com/video/stream.mpd"
        };
        var encoded = "aHR0cHM6Ly9zdHJlYW0ucHJvdmlkZXIuY29tL3ZpZGVvLm1wNA==";
        '''
        urls = scan_text_for_media_urls(text)
        self.assertTrue(any("live.m3u8" in u for u in urls))
        self.assertTrue(any("stream.mpd" in u for u in urls))
        self.assertTrue(any("video.mp4" in u for u in urls))

    def test_generic_harvester_script_blocks(self):
        from extractors.generic import generic_html_link_harvester
        packed_js = "eval(function(p,a,c,k,e,d){return p}(\"0 1='2://3.4/5.6';\",7,7,'var|videoUrl|https|cdn.test|example|stream|m3u8'.split('|'),0,{}))"
        html = f"<html><head><title>Test Stream</title></head><body><script>{packed_js}</script></body></html>"
        results = generic_html_link_harvester("https://example.com/movie/test", None, html=html)
        options = results.get("video_options", [])
        m3u8_opts = [o for o in options if "stream.m3u8" in o.get("url", "")]
        self.assertTrue(len(m3u8_opts) > 0)
        self.assertEqual(m3u8_opts[0].get("ext"), "mp4")
        self.assertEqual(m3u8_opts[0].get("type"), "video")

    def test_generic_harvester_iframe_query_param(self):
        from unittest.mock import patch
        from extractors.generic import generic_html_link_harvester
        html = '''
        <html><body>
        <iframe src="https://player.site.com/embed?url=https%3A%2F%2Fcdn.site.com%2Fvideo%2Fmaster.m3u8"></iframe>
        </body></html>
        '''
        with patch("extractors.generic.fetch_html", return_value=""):
            results = generic_html_link_harvester("https://example.com/movie/embed-test", None, html=html)
        options = results.get("video_options", [])
        found = [o for o in options if "master.m3u8" in o.get("url", "")]
        self.assertTrue(len(found) > 0)
        self.assertEqual(found[0].get("ext"), "mp4")
        self.assertEqual(found[0].get("type"), "video")

    def test_download_task_mse_stream_rejection(self):
        from unittest.mock import patch
        from config import downloads_status, downloads_status_lock
        from tasks.download import bg_download_task
        
        task_id = "test_mse_task_id"
        with downloads_status_lock:
            downloads_status[task_id] = {"status": "starting"}
            
        with patch("extractors.generic.fetch_html", return_value="<div>MediaSource and crypto.subtle player</div>"):
            bg_download_task(
                download_id=task_id,
                url="https://storage.googleapiscdn.com/player/test_ep",
                format_id="avs_ep_1",
                ext="mp4",
                quality="192",
                title="Anime Test"
            )
            
        with downloads_status_lock:
            status = downloads_status.get(task_id, {})
            self.assertEqual(status.get("status"), "error")
            self.assertIn("Luồng phát được mã hóa WebCrypto/MSE trong RAM trình duyệt", status.get("message", ""))

    def test_download_task_resolves_obfuscated_player(self):
        from unittest.mock import patch, MagicMock
        from config import downloads_status, downloads_status_lock
        from tasks.download import bg_download_task
        
        task_id = "test_resolve_player_task"
        with downloads_status_lock:
            downloads_status[task_id] = {"status": "starting"}

        obfuscated_html = r"<script>var video_source = '\x68\x74\x74\x70\x73\x3a\x2f\x2f\x63\x64\x6e\x2e\x6e\x65\x74\x2f\x73\x74\x72\x65\x61\x6d\x2e\x6d\x33\x75\x38';</script>"

        # Intercept before yt-dlp execution so we only test stream resolution
        with patch("extractors.generic.fetch_html", return_value=obfuscated_html), \
             patch("tasks.download.create_ydl_instance", side_effect=Exception("StopBeforeYtdlp")):
            try:
                bg_download_task(
                    download_id=task_id,
                    url="https://player.site.com/embed/movie123",
                    format_id="embed_opt_1",
                    ext="html",
                    quality="192",
                    title="Movie Title"
                )
            except Exception:
                pass

        with downloads_status_lock:
            status = downloads_status.get(task_id, {})
            # Should have attempted yt-dlp with the resolved m3u8 url
            self.assertIn("StopBeforeYtdlp", status.get("message", ""))

if __name__ == "__main__":
    unittest.main()
