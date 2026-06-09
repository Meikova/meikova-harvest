import requests
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

url = "https://p16-common-sign.tiktokcdn.com/tos-alisg-i-photomode-sg/0b596b1e4e4042f099cb8b1da8a75fd0~tplv-photomode-image.jpeg?dr=14555&x-expires=1781190000&x-signature=65Oxut7aSUKKHM00V%2B5CW1lBc1o%3D&t=4d5b0474&ps=13740610&shp=81f88b70&shcp=9b759fb9&idc=my2&ftpl=1"
cookies_file = "downloads/cookies/cookies_client_537ngrlf0hnuty574auzds.txt"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
}

session = requests.Session()
if os.path.exists(cookies_file):
    try:
        import http.cookiejar
        cookie_jar = http.cookiejar.MozillaCookieJar()
        cookie_jar.load(cookies_file, ignore_discard=True, ignore_expires=True)
        session.cookies.update(cookie_jar)
        print("Loaded cookies file successfully")
    except Exception as e:
        print("Failed to load cookies:", e)

print("Testing HEAD request WITH cookies...")
try:
    r = session.head(url, headers=headers, timeout=5)
    print("Status Code:", r.status_code)
    print("Content-Length:", r.headers.get("content-length"))
except Exception as e:
    print("Error:", e)
