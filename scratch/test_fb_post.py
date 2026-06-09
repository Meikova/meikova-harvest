import requests
import re
import json
import sys

url = "https://www.facebook.com/share/p/18KCdDUac7/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Fetch without cookies first
print("Fetching without cookies...")
r = requests.get(url, headers=headers, timeout=10)
print(f"Status: {r.status_code}")
print(f"HTML length: {len(r.text)}")

# Save HTML for inspection
with open("scratch/fb_post.html", "w", encoding="utf-8") as f:
    f.write(r.text)

print("Saved HTML to scratch/fb_post.html")
