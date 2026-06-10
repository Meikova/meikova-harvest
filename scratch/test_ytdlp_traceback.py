import yt_dlp
import traceback

url = "https://www.youtube.com/watch?v=eBm23CzA-w4"

ydl_opts = {
    "quiet": True,
    "no_warnings": False,
    "nocheckcertificate": True,
    "noplaylist": True,
    "impersonate": "chrome",
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print(f"Success! Title: {info.get('title')}")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
