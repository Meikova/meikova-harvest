import os
import requests
from http.cookiejar import MozillaCookieJar

cookies_file = r"D:\JOB\DEV\EveryThingDownloader\downloads\cookies\cookies_client_537ngrlf0hnuty574auzds.txt"
url_www = "https://www.facebook.com/stories/1893927050634982/UzpfSVNDOjk4MzQyMDY3MTI3NjY4Nw==/?bucket_count=9&source=story_tray"
url_m = "https://m.facebook.com/stories/1893927050634982/UzpfSVNDOjk4MzQyMDY3MTI3NjY4Nw==/?bucket_count=9&source=story_tray"

print("Loading cookies...")
cj = MozillaCookieJar(cookies_file)
try:
    cj.load(ignore_discard=True, ignore_expires=True)
    print("Loaded cookies successfully.")
    for cookie in cj:
        print(f"Cookie: {cookie.name} = {cookie.value[:10]}... for domain {cookie.domain}")
except Exception as e:
    print("Failed to load cookies:", e)

session = requests.Session()
session.cookies = cj

# Try requesting the mobile version
print("\n--- Requesting m.facebook.com ---")
headers_m = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}
try:
    res = session.get(url_m, headers=headers_m, timeout=10)
    print("Status Code:", res.status_code)
    print("Redirect History:", [r.url for r in res.history])
    print("Final URL:", res.url)
    print("Content Length:", len(res.text))
    # Look for video links in mobile HTML
    import re
    video_links = re.findall(r'https://video[^"]+?\.mp4[^"]*?', res.text)
    print("Found video links in mobile HTML:", len(video_links))
    for link in video_links[:5]:
        print("  ->", link.replace("\\", "")[:120])
except Exception as e:
    print("Request to m.facebook.com failed:", e)

# Try requesting the desktop version with full headers
print("\n--- Requesting www.facebook.com ---")
headers_www = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.facebook.com/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Upgrade-Insecure-Requests": "1"
}
try:
    res = session.get(url_www, headers=headers_www, timeout=10)
    print("Status Code:", res.status_code)
    print("Redirect History:", [r.url for r in res.history])
    print("Final URL:", res.url)
    print("Content Length:", len(res.text))
    # Look for image or video JSON keys
    import re
    matches = re.findall(r'"playable_url"\s*:\s*"([^"]+)"', res.text)
    print("Found playable_url matches:", len(matches))
    for m in matches[:3]:
        print("  ->", m.replace("\\/", "/")[:100])
except Exception as e:
    print("Request to www.facebook.com failed:", e)
