import yt_dlp
import requests
import os

url = "https://www.tiktok.com/@damtiensinh179/video/7645677753722768648"
cookie_file = "downloads/cookies/cookies_client_537ngrlf0hnuty574auzds.txt"

ydl_opts = {
    "cookiefile": cookie_file if os.path.exists(cookie_file) else None,
    "nocheckcertificate": True,
}

print(f"Extracting thumbnail for {url}...")
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    try:
        info = ydl.extract_info(url, download=False)
        thumbnail = info.get("thumbnail")
        print("Thumbnail URL:", thumbnail)
        if thumbnail:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.tiktok.com/"
            }
            r = requests.get(thumbnail, headers=headers)
            print("HTTP Status Code for image download:", r.status_code)
            if r.status_code == 200:
                print("Image download: SUCCESS")
            else:
                print("Image download: FAILED", r.text[:200])
    except Exception as e:
        print("Extract failed:", e)
