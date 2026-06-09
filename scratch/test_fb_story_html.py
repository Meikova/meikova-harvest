import sys
import os
import requests
import re
from http.cookiejar import MozillaCookieJar

url = "https://www.facebook.com/stories/1893927050634982/UzpfSVNDOjk4MzQyMDY3MTI3NjY4Nw==/?bucket_count=9&source=story_tray"
cookies_file = r"D:\JOB\DEV\EveryThingDownloader\downloads\cookies\cookies_client_537ngrlf0hnuty574auzds.txt"

print("Starting custom scraper test for Facebook Story...")

if not os.path.exists(cookies_file):
    print("Error: Cookies file not found.")
    sys.exit(1)

# Load Netscape cookies
cj = MozillaCookieJar(cookies_file)
cj.load(ignore_discard=True, ignore_expires=True)

# Convert to requests-compatible session
session = requests.Session()
session.cookies = cj

# Add user-agent
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
})

try:
    response = session.get(url, timeout=15)
    print("Response Status:", response.status_code)
    print("Response URL:", response.url)
    
    # Save a portion of HTML for debugging
    html = response.text
    print("HTML Length:", len(html))
    
    # Check if redirect to login occurred
    if "login.php" in response.url or "login" in html.lower() and "sign up" in html.lower() and len(html) < 20000:
        print("Redirected to login or very small login page. Cookies might be expired/invalid or not accepted.")
    
    # Search for video patterns
    # Facebook videos are often in JSON blobs in the HTML
    video_urls = []
    # Search for "playable_url" or "playable_url_quality_hd"
    patterns = [
        r'"playable_url"\s*:\s*"([^"]+)"',
        r'"playable_url_quality_hd"\s*:\s*"([^"]+)"',
        r'"browser_native_hd_url"\s*:\s*"([^"]+)"',
        r'"browser_native_sd_url"\s*:\s*"([^"]+)"',
        r'hd_src\s*:\s*"([^"]+)"',
        r'sd_src\s*:\s*"([^"]+)"',
        r'"video"\s*:\s*{\s*"resources"\s*:\s*\[[^\]]*"src"\s*:\s*"([^"]+)"',
        r'video_src\s*=\s*"([^"]+)"',
        r'https://video[^"]+?\.mp4[^"]*?'
    ]
    
    for pat in patterns:
        matches = re.findall(pat, html)
        if matches:
            print(f"Matched pattern '{pat}': found {len(matches)} matches")
            for m in matches[:5]:
                # unescape unicode/slashes
                clean = m.replace("\\/", "/").replace("\\u0025", "%")
                print("  ->", clean[:100])
                video_urls.append(clean)
                
    # Also look for images just in case it is a photo story
    image_patterns = [
        r'"preferred_thumbnail"\s*:\s*{\s*"image"\s*:\s*{\s*"uri"\s*:\s*"([^"]+)"',
        r'"overlay_image_uri"\s*:\s*"([^"]+)"'
    ]
    for pat in image_patterns:
        matches = re.findall(pat, html)
        if matches:
            print(f"Matched image pattern '{pat}': found {len(matches)} matches")
            for m in matches[:5]:
                clean = m.replace("\\/", "/")
                print("  ->", clean[:100])

    if not video_urls:
        print("No video URLs found in HTML source. Let's dump some script text to see the structure.")
        # Find all script blocks
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        print(f"Found {len(scripts)} script tags.")
        for idx, scr in enumerate(scripts):
            if "playable_url" in scr or "stories" in scr or "story" in scr or "video" in scr:
                print(f"Script {idx} contains interesting keywords. Length: {len(scr)}")
                # Print first 200 chars and last 200 chars
                print("  Start:", scr[:200])
                
except Exception as e:
    print("Scraper test failed:", e)
