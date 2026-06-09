import yt_dlp
import os
import json

url = "https://www.tiktok.com/@mi3k_18dp/video/7649036378268781842"
cookie_file = "downloads/cookies/cookies_client_537ngrlf0hnuty574auzds.txt"

ydl_opts = {
    "cookiefile": cookie_file if os.path.exists(cookie_file) else None,
    "nocheckcertificate": True,
}

print("Running recursive search on info dictionary...")

def find_urls(data, path=""):
    found = []
    if isinstance(data, dict):
        for k, v in data.items():
            found.extend(find_urls(v, f"{path}.{k}" if path else k))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            found.extend(find_urls(item, f"{path}[{idx}]"))
    elif isinstance(data, str):
        if "tiktokcdn.com" in data or "byteimg.com" in data or "ibyteimg.com" in data:
            found.append((path, data))
    return found

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    try:
        info = ydl.extract_info(url, download=False)
        print("Extract succeeded!")
        all_urls = find_urls(info)
        print(f"Found {len(all_urls)} CDN URLs:")
        for path, val in all_urls:
            print(f" - Path: {path}")
            print(f"   URL: {val[:120]}...")
    except Exception as e:
        print("Extract failed:", e)
