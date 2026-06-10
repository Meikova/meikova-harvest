import yt_dlp
import os
import sys
from yt_dlp.networking.impersonate import ImpersonateTarget

# Ensure output is utf-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

cookie_file = "scratch/user_cookies_netscape.txt"
url = "https://www.youtube.com/watch?v=eBm23CzA-w4"
out_dir = "scratch/test_download_output"
os.makedirs(out_dir, exist_ok=True)

ydl_opts = {
    "outtmpl": os.path.join(out_dir, "media.%(ext)s"),
    "nocheckcertificate": True,
    "quiet": False,
    "verbose": True,
    "no_warnings": False,
    "noplaylist": True,
    "cookiefile": cookie_file,
    "js_runtimes": {"node": {}},
    "impersonate": ImpersonateTarget.from_str("chrome") if ImpersonateTarget else None,
    "extractor_args": {
        "youtube": {
            "player_client": ["default"],
        }
    },
    "format": "bestvideo[height<=360]+bestaudio/best[height<=360]" # Limit height for fast test download
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print("Starting download...")
        ret = ydl.download([url])
        print(f"Download finished with return code: {ret}")
except Exception as e:
    print(f"Failed: {e}")
