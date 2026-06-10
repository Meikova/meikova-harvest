import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
import logging

url = "https://www.youtube.com/watch?v=eBm23CzA-w4"

ydl_opts = {
    "verbose": True,
    "nocheckcertificate": True,
    "noplaylist": True,
    "impersonate": ImpersonateTarget.from_str("chrome"),
}

print("--- Testing default backend with verbose=True ---")
try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(url, download=False)
except Exception as e:
    print("Error:", e)
