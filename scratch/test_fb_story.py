import sys
import os
import logging
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_fb")

url = "https://www.facebook.com/stories/1893927050634982/UzpfSVNDOjk4MzQyMDY3MTI3NjY4Nw==/?bucket_count=9&source=story_tray"

# Path to the uploaded cookies file
cookies_file = r"D:\JOB\DEV\EveryThingDownloader\downloads\cookies\cookies_client_537ngrlf0hnuty574auzds.txt"

ydl_opts = {
    "quiet": False,
    "no_warnings": False,
    "cookiefile": cookies_file,
    "js_runtimes": {"deno": {}, "node": {}, "bun": {}, "quickjs": {}},
}

print("Testing Facebook Story URL extraction...")
if os.path.exists(cookies_file):
    print(f"Using cookies file: {cookies_file}")
else:
    print(f"Warning: cookies file not found at {cookies_file}")

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print("Success! Extracted info keys:", info.keys() if info else "None")
except Exception as e:
    print("Failed extraction with exception:", e)
