import unittest
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

class TestAnimeVietSubPreview(unittest.TestCase):
    def test_clean_iframe_preserves_is_final(self):
        # Verify that stripping tracking params preserves isFinal=1
        iframe_link = "https://storage.googleapiscdn.com/player/36e192e3aa258a09b5c6e6b1241c24192fe40287978f308fe635461546bab03e?isFinal=1&nextName=Ep2&nextUrl=/next"
        parsed = urlparse(iframe_link)
        iframe_qs = parse_qs(parsed.query, keep_blank_values=True)
        iframe_qs.pop("nextName", None)
        iframe_qs.pop("nextUrl", None)
        new_query = urlencode(iframe_qs, doseq=True)
        clean_iframe = urlunparse(parsed._replace(query=new_query))
        
        self.assertIn("isFinal=1", clean_iframe)
        self.assertNotIn("nextName", clean_iframe)
        self.assertNotIn("nextUrl", clean_iframe)

    def test_init_js_patching(self):
        # Verify that init.min.js functions are neutralized correctly
        mock_init_js = "function _avsShowBrowserUpgradeNotice(){var x=1;}function _runCompatBootstrap(){alert(1);}"
        patched_js = mock_init_js.replace(
            "function _avsShowBrowserUpgradeNotice(){",
            "function _avsShowBrowserUpgradeNotice(){return;"
        ).replace(
            "function _runCompatBootstrap(){",
            "function _runCompatBootstrap(){try{if(typeof startPlayer==='function')startPlayer();}catch(e){};return;"
        )
        self.assertIn("function _avsShowBrowserUpgradeNotice(){return;", patched_js)
        self.assertIn("startPlayer()", patched_js)

    def test_url_is_final_enforcement(self):
        url = "https://storage.googleapiscdn.com/player/test123"
        if "googleapiscdn.com/player/" in url and "isFinal=" not in url:
            url += ("&" if "?" in url else "?") + "isFinal=1"
        self.assertEqual(url, "https://storage.googleapiscdn.com/player/test123?isFinal=1")

    def test_episode_url_detection(self):
        import re
        url = "https://animevietsub.nl/phim/the-gioi-phep-thuat-a474/tap-02-42082.html"
        url_ep_match = re.search(r'tap-(\d+)', url.lower())
        self.assertIsNotNone(url_ep_match)
        self.assertEqual(url_ep_match.group(1), "02")
        self.assertEqual(url_ep_match.group(1).lstrip("0"), "2")

    def test_episode_is_current_matching(self):
        import re
        url = "https://animevietsub.nl/phim/the-gioi-phep-thuat-a474/tap-02-42082.html"
        url_ep_match = re.search(r'tap-(\d+)', url.lower())
        url_ep_num = url_ep_match.group(1) if url_ep_match else ""

        episodes = [
            ("42081", "Tập 01", "/tap-01-42081.html", "1"),
            ("42082", "Tập 02", "/tap-02-42082.html", "2"),
            ("42083", "Tập 03", "/tap-03-42083.html", "3"),
        ]

        results = []
        for ep_data_id, ep_title_attr, ep_href, ep_num in episodes:
            is_current = False
            if ep_href and (ep_href in url or url.endswith(ep_href)):
                is_current = True
            elif url_ep_num and (ep_num.lstrip('0') == url_ep_num.lstrip('0')):
                is_current = True
            results.append((ep_title_attr, is_current))

        self.assertEqual(results, [
            ("Tập 01", False),
            ("Tập 02", True),
            ("Tập 03", False)
        ])

if __name__ == "__main__":
    unittest.main()
