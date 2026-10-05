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

if __name__ == "__main__":
    unittest.main()
