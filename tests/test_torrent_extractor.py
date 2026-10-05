import os
import sys
import unittest
import tempfile
import hashlib
from extractors.torrent import (
    is_torrent_input,
    parse_magnet_uri,
    bdecode_torrent,
    extract_torrent_info,
    format_size
)
from app import app

def bencode(obj):
    """Helper to generate valid bencoded data for testing."""
    if isinstance(obj, str):
        b = obj.encode('utf-8')
        return f"{len(b)}:".encode('ascii') + b
    elif isinstance(obj, bytes):
        return f"{len(obj)}:".encode('ascii') + obj
    elif isinstance(obj, int):
        return f"i{obj}e".encode('ascii')
    elif isinstance(obj, list):
        return b'l' + b''.join(bencode(x) for x in obj) + b'e'
    elif isinstance(obj, dict):
        items = sorted((k.encode('utf-8') if isinstance(k, str) else k, v) for k, v in obj.items())
        return b'd' + b''.join(bencode(k) + bencode(v) for k, v in items) + b'e'
    raise TypeError(type(obj))

class TestTorrentExtractor(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_is_torrent_input_detection(self):
        # Magnet links
        self.assertTrue(is_torrent_input("magnet:?xt=urn:btih:3b10b054b1680110d403788034f51763ac43791e&dn=Ubuntu"))
        self.assertTrue(is_torrent_input("MAGNET:?XT=URN:BTIH:3B10B054B1680110D403788034F51763AC43791E"))
        
        # 40-char Hex Hashes
        self.assertTrue(is_torrent_input("3b10b054b1680110d403788034f51763ac43791e"))
        self.assertTrue(is_torrent_input("AABBCCDDEEFF0011223344556677889900AABBCC"))

        # Base32 Hashes (32 chars)
        self.assertTrue(is_torrent_input("HMZLCVFVNAABBUDTHB5UOF3CZZM334WB"))

        # Remote .torrent URLs
        self.assertTrue(is_torrent_input("https://releases.ubuntu.com/24.04/ubuntu-24.04-desktop-amd64.iso.torrent"))
        self.assertTrue(is_torrent_input("http://example.com/download.torrent?token=123"))

        # Negative tests
        self.assertFalse(is_torrent_input("https://www.youtube.com/watch?v=DzOF3gUEqkY"))
        self.assertFalse(is_torrent_input("https://tiktok.com/@user/video/123"))
        self.assertFalse(is_torrent_input(""))

    def test_parse_magnet_uri(self):
        magnet = "magnet:?xt=urn:btih:3b10b054b1680110d403788034f51763ac43791e&dn=Ubuntu+24.04+LTS&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&xl=4500000000"
        res = parse_magnet_uri(magnet)
        self.assertEqual(res["info_hash"], "3b10b054b1680110d403788034f51763ac43791e")
        self.assertEqual(res["name"], "Ubuntu 24.04 LTS")
        self.assertEqual(len(res["trackers"]), 1)
        self.assertEqual(res["trackers"][0], "udp://tracker.opentrackr.org:1337/announce")
        self.assertEqual(res["total_bytes"], 4500000000)

    def test_bdecode_and_info_hash(self):
        info_dict = {
            'name': 'Test Video.mp4',
            'length': 1048576,
            'piece length': 16384,
            'pieces': b'12345678901234567890'
        }
        torrent_data = {
            'announce': 'http://tracker.example.com:80',
            'info': info_dict
        }
        raw_torrent = bencode(torrent_data)
        raw_info = bencode(info_dict)
        expected_hash = hashlib.sha1(raw_info).hexdigest()
        
        parsed, computed_hash = bdecode_torrent(raw_torrent)
        
        self.assertEqual(computed_hash, expected_hash)
        self.assertEqual(parsed[b'info'][b'name'], b'Test Video.mp4')
        self.assertEqual(parsed[b'info'][b'length'], 1048576)

    def test_extract_local_torrent_file(self):
        # Create a temporary .torrent file with multi-file structure
        with tempfile.NamedTemporaryFile(suffix=".torrent", delete=False) as f:
            torrent_path = f.name
            info_dict = {
                'name': 'AnimeSeries',
                'piece length': 32768,
                'pieces': b'00000000000000000000',
                'files': [
                    {'length': 5242880, 'path': ['episode1.mp4']},
                    {'length': 2097152, 'path': ['soundtrack.mp3']},
                    {'length': 102400, 'path': ['poster.jpg']}
                ]
            }
            torrent_data = {
                'announce': 'http://tracker.example.com/ann',
                'created by': 'uTorrent/3.5.5',
                'creation date': 1710000000,
                'info': info_dict
            }
            f.write(bencode(torrent_data))

        try:
            info = extract_torrent_info(torrent_path)
            self.assertEqual(info["status"], "success")
            self.assertEqual(info["title"], "AnimeSeries")
            self.assertEqual(info["platform_class"], "torrent")
            self.assertTrue("uTorrent" in info["uploader"])
            
            # Check categorized options
            video_labels = [opt["label"] for opt in info["video_options"]]
            audio_labels = [opt["label"] for opt in info["audio_options"]]
            image_labels = [img["label"] for img in info["images"]]
            
            self.assertTrue(any("episode1.mp4" in l for l in video_labels))
            self.assertTrue(any("soundtrack.mp3" in l for l in audio_labels))
            self.assertTrue(any("poster.jpg" in l for l in image_labels))
        finally:
            if os.path.exists(torrent_path):
                os.remove(torrent_path)

    def test_api_info_magnet_integration(self):
        magnet = "magnet:?xt=urn:btih:3b10b054b1680110d403788034f51763ac43791e&dn=Ubuntu+24.04+LTS"
        response = self.client.post("/api/info", json={"url": magnet})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["title"], "Ubuntu 24.04 LTS")
        self.assertEqual(data["platform_class"], "torrent")
        self.assertEqual(data["id"], "3b10b054b1680110d403788034f51763ac43791e")
        self.assertTrue(len(data["video_options"]) >= 1)

    def test_quoted_paths_and_local_file_detection(self):
        # 1. Quoted magnet and paths detection
        self.assertTrue(is_torrent_input('"magnet:?xt=urn:btih:3b10b054b1680110d403788034f51763ac43791e"'))
        self.assertTrue(is_torrent_input("'magnet:?xt=urn:btih:3b10b054b1680110d403788034f51763ac43791e'"))
        self.assertTrue(is_torrent_input('"E:\\Downloads\\spider-man-brand-new-day_archive.torrent"'))

        # 2. Create a temporary .torrent file and a sibling mp4 file
        with tempfile.TemporaryDirectory() as temp_folder:
            torrent_file = os.path.join(temp_folder, "test_movie.torrent")
            mp4_file = os.path.join(temp_folder, "movie.mp4")
            with open(mp4_file, "wb") as f_mp4:
                f_mp4.write(b"fake mp4 video bytes")

            info_dict = {
                'name': 'TestMovie',
                'piece length': 16384,
                'pieces': b'00000000000000000000',
                'files': [{'length': 20, 'path': ['movie.mp4']}]
            }
            torrent_data = {
                'announce': 'http://tracker.example.com',
                'info': info_dict
            }
            with open(torrent_file, "wb") as f_tor:
                f_tor.write(bencode(torrent_data))

            # Test with quotes around path
            quoted_torrent_path = f'"{torrent_file}"'
            resp = self.client.post("/api/info", json={"url": quoted_torrent_path})
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["title"], "TestMovie")
            
            # Verify sibling mp4 was detected as existing local file
            movie_opt = next((o for o in data["video_options"] if "movie.mp4" in o["label"]), None)
            self.assertIsNotNone(movie_opt)
            self.assertTrue(movie_opt.get("is_local"))
            self.assertTrue(movie_opt.get("url").endswith("movie.mp4"))

    def test_sys_import_in_download_task(self):
        from unittest.mock import patch
        from tasks.download import bg_download_task
        from config import downloads_status, downloads_status_lock
        
        # Test that downloading a magnet link does not raise NameError: name 'sys' is not defined
        test_id = "test_sys_import_check"
        with downloads_status_lock:
            downloads_status[test_id] = {"status": "pending"}
            
        magnet = "magnet:?xt=urn:btih:3b10b054b1680110d403788034f51763ac43791e&dn=Test"
        with patch("os.startfile", create=True) as mock_startfile:
            bg_download_task(test_id, magnet, "torrent_magnet_save", "magnet", "Direct P2P", "Test Magnet")
        
        with downloads_status_lock:
            status = downloads_status.get(test_id, {})
            self.assertNotEqual(status.get("error"), "name 'sys' is not defined")
            self.assertEqual(status.get("status"), "complete")

    def test_extension_categorization_and_webseeds(self):
        with tempfile.NamedTemporaryFile(suffix=".torrent", delete=False) as f:
            torrent_path = f.name
            info_dict = {
                'name': 'spider-man-brand-new-day',
                'piece length': 32768,
                'pieces': b'00000000000000000000',
                'files': [
                    {'length': 1234567, 'path': ['SPIDER-MAN on Set.mp4']},
                    {'length': 50000, 'path': ['spider-man_meta.sqlite']},
                    {'length': 15000, 'path': ['spider-man_files.xml']},
                    {'length': 40000, 'path': ['archive.zip']}
                ]
            }
            torrent_data = {
                'announce': 'http://tracker.archive.org',
                'created by': 'Internet Archive',
                'url-list': ['https://archive.org/download/spider-man-brand-new-day/'],
                'info': info_dict
            }
            f.write(bencode(torrent_data))

        try:
            info = extract_torrent_info(torrent_path)
            self.assertEqual(info["status"], "success")
            
            # Check package option
            package_opt = next(o for o in info["video_options"] if o.get("format_id") == "torrent_file_download")
            self.assertEqual(package_opt["type"], "torrent")
            self.assertTrue(package_opt.get("is_package"))

            # Check MP4 video
            mp4_opt = next(o for o in info["video_options"] if "SPIDER-MAN on Set.mp4" in o["label"])
            self.assertEqual(mp4_opt["type"], "video")
            self.assertTrue(mp4_opt.get("is_webseed"))
            self.assertTrue(mp4_opt["url"].startswith("https://archive.org/download/spider-man-brand-new-day/"))
            self.assertTrue("SPIDER-MAN" in mp4_opt["url"])

            # Check SQLite data
            sqlite_opt = next(o for o in info["video_options"] if "spider-man_meta.sqlite" in o["label"])
            self.assertEqual(sqlite_opt["type"], "data")
            self.assertTrue(sqlite_opt.get("is_webseed"))

            # Check XML text
            xml_opt = next(o for o in info["video_options"] if "spider-man_files.xml" in o["label"])
            self.assertEqual(xml_opt["type"], "text")
            self.assertTrue(xml_opt.get("is_webseed"))

            # Check ZIP archive
            zip_opt = next(o for o in info["video_options"] if "archive.zip" in o["label"])
            self.assertEqual(zip_opt["type"], "archive")
            self.assertTrue(zip_opt.get("is_webseed"))
        finally:
            if os.path.exists(torrent_path):
                os.remove(torrent_path)

if __name__ == "__main__":
    unittest.main()

