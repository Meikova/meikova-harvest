"""Direct yt-dlp test matching the create_ydl_instance flow in info.py."""
import sys, os, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import yt_dlp
from config import TEMP_DOWNLOAD_DIR

url = "https://www.facebook.com/reel/769241986206453"
client_id = "client_lvnnn0l2zy8d6g9idw3j9a"
cookie_file = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")

# Try with cookies (like create_ydl_instance does)
ydl_opts = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "cookiefile": cookie_file,
    "impersonate": "chrome",
}

print("=== Test 1: With cookies + impersonate (matching app flow) ===")
info = None
try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    print(f"  title: {info.get('title', 'N/A')[:100]}")
    print(f"  thumbnail: {str(info.get('thumbnail', 'N/A'))[:100]}")
    print(f"  duration: {info.get('duration', 'N/A')}")
    print(f"  upload_date: {info.get('upload_date', 'N/A')}")
    print(f"  view_count: {info.get('view_count', 'N/A')}")
except Exception as e:
    print(f"  FAILED: {e}")

# Try without cookies (retry flow)
print("\n=== Test 2: Without cookies (retry flow) ===")
ydl_opts2 = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
}
info2 = None
try:
    with yt_dlp.YoutubeDL(ydl_opts2) as ydl:
        info2 = ydl.extract_info(url, download=False)
    print(f"  title: {info2.get('title', 'N/A')[:100]}")
    print(f"  thumbnail: {str(info2.get('thumbnail', 'N/A'))[:100]}")
    print(f"  duration: {info2.get('duration', 'N/A')}")
    print(f"  upload_date: {info2.get('upload_date', 'N/A')}")
    print(f"  view_count: {info2.get('view_count', 'N/A')}")
except Exception as e:
    print(f"  FAILED: {e}")
