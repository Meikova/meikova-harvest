import sys
import os
sys.path.append(os.path.abspath('.'))

import requests
import re

url = "https://www.facebook.com/reel/1263752559080744"
cookies_file = "downloads/cookies/cookies_client_537ngrlf0hnuty574auzds.txt"

# Parse Netscape cookie file
cookies = {}
if os.path.exists(cookies_file):
    with open(cookies_file, 'r') as f:
        for line in f:
            if not line.strip() or line.startswith('#'):
                continue
            parts = line.strip().split('\t')
            if len(parts) >= 7:
                domain = parts[0]
                name = parts[5]
                value = parts[6]
                cookies[name] = value

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
}

print("Fetching desktop page...")
resp = requests.get(url, cookies=cookies, headers=headers)
print("Status Code:", resp.status_code)

title_match = re.search(r'<title>(.*?)</title>', resp.text, re.IGNORECASE)
if title_match:
    print("Page Title:", title_match.group(1))
else:
    print("No title tag found.")

# Let's search for patterns like "reactions" or "likes" or "Bí Mật Cậu Nhỏ"
print("\nSearching for reactions/likes pattern in HTML...")
matches = re.findall(r'(\d+[\d.,]*\s*(?:reactions|likes|lượt thích|cảm xúc))', resp.text, re.IGNORECASE)
print("Matches found:", matches[:20])

# Let's save the first 100000 characters of HTML to inspect
with open("scratch/fb_reel_desktop.html", "w", encoding="utf-8") as f:
    f.write(resp.text[:500000])
print("Saved HTML snippet to scratch/fb_reel_desktop.html")
