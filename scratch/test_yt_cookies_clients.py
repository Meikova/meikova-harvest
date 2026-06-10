import yt_dlp
import sys
import os
from yt_dlp.networking.impersonate import ImpersonateTarget

# Ensure output is utf-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

cookie_file = "downloads/cookies/cookies_client_lvnnn0l2zy8d6g9idw3j9a.txt"
url = "https://www.youtube.com/watch?v=eBm23CzA-w4"

client_combinations = [
    # Default as configured currently
    ["default", "-tv", "-tv_downgraded"],
    # Allow tv/tv_downgraded
    ["default"],
    # Try web only
    ["web"],
    # Try mweb only
    ["mweb"],
    # Try ios / android (they don't support cookies but let's see)
    ["android", "ios"],
    # Try ios only
    ["ios"],
    # Try android only
    ["android"],
    # Try web_embedded only
    ["web_embedded"],
    # Try android_vr only
    ["android_vr"]
]

for idx, clients in enumerate(client_combinations):
    print(f"\n--- Test {idx}: player_client={clients} ---")
    ydl_opts = {
        "quiet": True,
        "no_warnings": False,
        "nocheckcertificate": True,
        "noplaylist": True,
        "cookiefile": cookie_file,
        "impersonate": ImpersonateTarget.from_str("chrome"),
        "extractor_args": {
            "youtube": {
                "player_client": clients,
            }
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])
            print(f"Success! Extracted {len(formats)} formats.")
            for f in formats[:3]:
                print(f"  Format: {f.get('format_id')} - {f.get('resolution')} ({f.get('ext')})")
    except Exception as e:
        print(f"Failed: {e}")
