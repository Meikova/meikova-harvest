import os
import requests
from http.cookiejar import MozillaCookieJar

cookies_file = r"D:\JOB\DEV\EveryThingDownloader\downloads\cookies\cookies_client_537ngrlf0hnuty574auzds.txt"
url = "https://www.facebook.com/stories/729012027223830/UzpfSVNDOjE1MzIxMzM0MDE4MzY2Mzc=/?bucket_count=9&source=story_tray"

print("Checking cookies file path...")
if not os.path.exists(cookies_file):
    print("Error: Cookies file not found.")
    exit(1)

cj = MozillaCookieJar(cookies_file)
cj.load(ignore_discard=True, ignore_expires=True)

session = requests.Session()
session.cookies = cj

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.facebook.com/",
    "Upgrade-Insecure-Requests": "1"
}

print("Requesting Facebook Story URL...")
try:
    res = session.get(url, headers=headers, timeout=15)
    print("Response Status Code:", res.status_code)
    print("Final Redirect URL:", res.url)
    
    html = res.text
    print("HTML Length:", len(html))
    
    # Write HTML to scratch folder
    output_path = r"D:\JOB\DEV\EveryThingDownloader\scratch\fb_story_dump.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved HTML dump to {output_path}")
    
    # Check if redirect to login occurred
    if "login.php" in res.url:
        print("Warning: Redirected to login page. Session cookies might be invalid or expired.")
        
except Exception as e:
    print("Error:", e)
