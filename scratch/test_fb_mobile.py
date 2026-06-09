import requests
import re

url = "https://mbasic.facebook.com/share/p/18KCdDUac7/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

print("Fetching from mbasic...")
r = requests.get(url, headers=headers, timeout=10)
print(f"Status: {r.status_code}")
print(f"Final URL: {r.url}")
print(f"HTML length: {len(r.text)}")

# Save HTML
with open("scratch/fb_mobile.html", "w", encoding="utf-8") as f:
    f.write(r.text)

print("Saved HTML to scratch/fb_mobile.html")
