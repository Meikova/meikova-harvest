import urllib.request
import re
import os
import sys

# Reconfigure stdout to use UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

url = "https://www.instagram.com/reel/DYYI6pbPhR_/"
client_id = "client_537ngrlf0hnuty574auzds"
client_cookies = os.path.join("downloads", "cookies", f"cookies_{client_id}.txt")

cookies_dict = {}
if os.path.exists(client_cookies):
    with open(client_cookies, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) >= 7:
                cookies_dict[parts[5]] = parts[6]

cookie_str = "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])
req = urllib.request.Request(url, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cookie": cookie_str,
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
})

try:
    with urllib.request.urlopen(req) as res:
        html = res.read().decode("utf-8", errors="ignore")
        print("Successfully fetched HTML. Length:", len(html))
        
        # Save HTML
        with open("scratch/reel_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        # Search for any matches of play count
        # Look for "play_count" or "video_play_count" or "playCount"
        matches = []
        for m in re.finditer(r'["\'](?:play_count|video_play_count|playCount|views|view_count)["\']\s*:\s*(\d+|"[^"]+")', html):
            matches.append(m.group(0))
            
        print("Matches found in JSON/JS script blocks:")
        for m in list(set(matches))[:15]:
            print("  -", m)
except Exception as e:
    print("Failed to fetch Reel page:", e)
