import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
import traceback

url = "https://www.youtube.com/watch?v=eBm23CzA-w4"

target = ImpersonateTarget.from_str("chrome")

ydl_opts = {
    "quiet": True,
    "no_warnings": False,
    "nocheckcertificate": True,
    "noplaylist": True,
    "impersonate": target,
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print("Success!")
        print("Title (repr):", repr(info.get("title")))
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
