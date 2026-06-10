import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
import traceback

url = "https://www.youtube.com/watch?v=eBm23CzA-w4"

ydl_opts = {
    "quiet": True,
    "no_warnings": False,
    "nocheckcertificate": True,
    "noplaylist": True,
    "impersonate": ImpersonateTarget.from_str("chrome"),
    "extractor_args": {
        "youtube": {
            "player_client": ["default", "-tv", "-tv_downgraded"],
        }
    }
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print("Success!")
        formats = info.get("formats", [])
        print(f"Number of formats extracted: {len(formats)}")
        for f in formats[:5]:
            print(f"  Format: {f.get('format_id')} - {f.get('resolution')} ({f.get('ext')})")
except Exception as e:
    print("Error:", e)
    traceback.print_exc()
