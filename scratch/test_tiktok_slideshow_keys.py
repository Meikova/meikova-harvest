import yt_dlp
import os
import json

url = "https://www.tiktok.com/@mi3k_18dp/video/7649036378268781842"
cookie_file = "downloads/cookies/cookies_client_537ngrlf0hnuty574auzds.txt"

ydl_opts = {
    "cookiefile": cookie_file if os.path.exists(cookie_file) else None,
    "nocheckcertificate": True,
}

print(f"Extracting metadata for {url}...")
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    try:
        info = ydl.extract_info(url, download=False)
        print("Extract succeeded!")
        print("Keys in info:", list(info.keys()))
        
        # Check entries
        entries = info.get("entries")
        if entries:
            print(f"Found {len(entries)} entries")
            for i, entry in enumerate(entries):
                print(f"Entry {i} keys:", list(entry.keys()))
                print(f"Entry {i} url:", entry.get("url"))
                print(f"Entry {i} thumbnails:", len(entry.get("thumbnails", [])))
        
        # Check thumbnails
        thumbnails = info.get("thumbnails") or []
        print(f"Found {len(thumbnails)} thumbnails in main info")
        for i, t in enumerate(thumbnails[:15]):
            print(f"  Thumb {i}: {t.get('url')[:100]}...")
            
    except Exception as e:
        print("Extract failed:", e)
