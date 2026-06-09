import yt_dlp
import os
import json

url = "https://www.tiktok.com/@damtiensinh179/video/7645677753722768648"
cookie_file = "downloads/cookies/cookies_client_537ngrlf0hnuty574auzds.txt"

ydl_opts = {
    "cookiefile": cookie_file if os.path.exists(cookie_file) else None,
    "nocheckcertificate": True,
}

print(f"Extracting metadata for {url} using cookiefile={ydl_opts['cookiefile']}...")
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    try:
        info = ydl.extract_info(url, download=False)
        print("Extract succeeded!")
        print("Extractor:", info.get("extractor"))
        print("Formats list:")
        for f in info.get("formats", []):
            print(f"Format ID: {f.get('format_id')}")
            print(f"  Note: {f.get('format_note')}")
            print(f"  Ext: {f.get('ext')}")
            print(f"  Url: {f.get('url')[:100]}...")
            print(f"  vcodec: {f.get('vcodec')}")
    except Exception as e:
        print("Extract failed:", e)
