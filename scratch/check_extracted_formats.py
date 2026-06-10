import yt_dlp
import sys
from yt_dlp.networking.impersonate import ImpersonateTarget

# Ensure output is utf-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

cookie_file = "scratch/user_cookies_netscape.txt"
url = "https://www.youtube.com/watch?v=eBm23CzA-w4"

ydl_opts = {
    "quiet": True,
    "no_warnings": False,
    "nocheckcertificate": True,
    "noplaylist": True,
    "cookiefile": cookie_file,
    "js_runtimes": {"node": {}},
    "impersonate": ImpersonateTarget.from_str("chrome") if ImpersonateTarget else None,
    "extractor_args": {
        "youtube": {
            "player_client": ["default"],
        }
    }
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get("formats", [])
        print(f"Success! Extracted {len(formats)} formats:")
        for f in formats:
            f_id = f.get('format_id')
            res = f.get('resolution')
            ext = f.get('ext')
            vcodec = f.get('vcodec')
            acodec = f.get('acodec')
            note = f.get('format_note')
            url_val = f.get('url', '')
            has_drm = "drm" in url_val.lower() or "manifest" in url_val.lower()
            print(f"  Format {f_id}: {res} ({ext}) | vcodec={vcodec}, acodec={acodec} | note={note} | URL contains manifest/DRM={has_drm}")
except Exception as e:
    print(f"Failed: {e}")
