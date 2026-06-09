import requests
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Sample TikTok CDN image URL from the previous output
url = "https://p16-common-sign.tiktokcdn.com/tos-alisg-i-photomode-sg/0b596b1e4e4042f099cb8b1da8a75fd0~tplv-photomode-image.jpeg?dr=14555&x-expires=1781190000&x-signature=65Oxut7aSUKKHM00V%2B5CW1lBc1o%3D&t=4d5b0474&ps=13740610&shp=81f88b70&shcp=9b759fb9&idc=my2&ftpl=1"

# Test WITHOUT Referer
headers_no_ref = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
}
print("Testing HEAD request WITHOUT Referer...")
try:
    r = requests.head(url, headers=headers_no_ref, timeout=5)
    print("Status Code:", r.status_code)
    print("Content-Length:", r.headers.get("content-length"))
except Exception as e:
    print("Error:", e)

# Test WITH Referer
headers_with_ref = headers_no_ref.copy()
headers_with_ref["Referer"] = "https://www.tiktok.com/"
print("\nTesting HEAD request WITH Referer...")
try:
    r = requests.head(url, headers=headers_with_ref, timeout=5)
    print("Status Code:", r.status_code)
    print("Content-Length:", r.headers.get("content-length"))
except Exception as e:
    print("Error:", e)
