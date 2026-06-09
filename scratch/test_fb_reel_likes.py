import sys
import os
sys.path.append(os.path.abspath('.'))

import yt_dlp
import json

url = "https://www.facebook.com/reel/1263752559080744"
cookies_file = "downloads/cookies/cookies_client_537ngrlf0hnuty574auzds.txt"

ydl_opts = {
    'ignoreerrors': True,
    'no_color': True,
}
if os.path.exists(cookies_file):
    ydl_opts['cookiefile'] = cookies_file
    print("Using cookies file:", cookies_file)

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    if info:
        print("like_count:", info.get("like_count"))
        print("view_count:", info.get("view_count"))
        print("comment_count:", info.get("comment_count"))
        print("repost_count:", info.get("repost_count"))
        print("like_count class:", type(info.get("like_count")))
        
        # Save a subset of the info to a JSON file for deep inspection
        clean_info = {k: v for k, v in info.items() if k not in ['formats', 'requested_formats', 'thumbnails', 'http_headers']}
        with open("scratch/fb_reel_info_dump.json", "w", encoding="utf-8") as f:
            json.dump(clean_info, f, indent=2, ensure_ascii=False)
        print("Saved info dump to scratch/fb_reel_info_dump.json")
    else:
        print("Failed to extract info.")
