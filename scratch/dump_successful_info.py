import yt_dlp
import os
import json
import time

url = "https://www.tiktok.com/@mi3k_18dp/video/7649036378268781842"
cookie_file = "downloads/cookies/cookies_client_537ngrlf0hnuty574auzds.txt"

ydl_opts = {
    "cookiefile": cookie_file if os.path.exists(cookie_file) else None,
    "nocheckcertificate": True,
}

print("Trying to extract info and dump to JSON...")
for attempt in range(1, 6):
    print(f"Attempt {attempt}...")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print("SUCCESS!")
            # Dump to file
            with open("scratch/tiktok_info.json", "w", encoding="utf-8") as f:
                json.dump(info, f, indent=2, ensure_ascii=False)
            print("Saved info to scratch/tiktok_info.json")
            break
    except Exception as e:
        print(f"Attempt {attempt} failed: {e}")
        time.sleep(2)
