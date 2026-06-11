import sys
import os
import json
import re
import urllib.parse
import html as html_lib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from extractors.facebook import scrape_fb_post

url = "https://www.facebook.com/share/p/1B9Tkjw1tE/"
client_id = "client_lvnnn0l2zy8d6g9idw3j9a"

# Run a custom extraction loop to inspect intermediate values
cookies_dir = os.path.join("d:\\JOB\\DEV\\EveryThingDownloader\\", "downloads", "cookies") # actually TEMP_DOWNLOAD_DIR is in config
from config import TEMP_DOWNLOAD_DIR
cookie_file = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")

command = [
    "curl", "-s", "-L",
    "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "-H", "Accept-Language: vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
]
if os.path.exists(cookie_file):
    command.extend(["-b", cookie_file])
command.append(url)

import subprocess
res = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
html = res.stdout

canonical_match = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', html) or re.search(r'<meta\s+property="og:url"\s+content="([^"]+)"', html)
canonical_url = canonical_match.group(1) if canonical_match else url

print("Canonical URL:", canonical_url)

post_id = None
for target_url in [canonical_url, url]:
    if post_id:
        break
    m = re.search(r'/posts/([^/?#]+)', target_url)
    if m:
        post_id = m.group(1)
        print("Found post_id via /posts/:", post_id)
        continue
    m = re.search(r'story_fbid=([^&#]+)', target_url)
    if m:
        post_id = m.group(1)
        print("Found post_id via story_fbid:", post_id)
        continue
    m = re.search(r'[?&]fbid=([^&#]+)', target_url)
    if m:
        post_id = m.group(1)
        print("Found post_id via fbid:", post_id)
        continue
    m = re.search(r'/photos/[^/]+/([^/?#]+)', target_url)
    if m:
        post_id = m.group(1)
        print("Found post_id via /photos/:", post_id)
        continue

if not post_id:
    # Try share token
    share_token = None
    share_match = re.search(r'/share/[vp]/([^/?#]+)', url)
    if share_match:
        share_token = share_match.group(1)
    print("Share token:", share_token)
    if share_token:
        script_blocks = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
        for script_text in script_blocks:
            if share_token in script_text:
                permalink_urls = re.findall(r'"url"\s*:\s*"([^"]*permalink[^"]*)"', script_text)
                for pu in permalink_urls:
                    decoded = pu.replace("\\/", "/").replace("\\u00253A", ":").replace("\\u00252F", "/").replace("\\u0025", "%")
                    decoded = urllib.parse.unquote(decoded)
                    perm = re.search(r'/permalink/(\d+)', decoded)
                    if perm:
                        post_id = perm.group(1)
                        print("Found post_id via share token permalink:", post_id)
                        break
                if post_id:
                    break
                posts_urls = re.findall(r'"url"\s*:\s*"([^"]*\/posts\/[^"]*)"', script_text)
                for pu in posts_urls:
                    decoded = pu.replace("\\/", "/")
                    pm = re.search(r'/posts/([^/?#]+)', decoded)
                    if pm:
                        post_id = pm.group(1)
                        print("Found post_id via share token posts:", post_id)
                        break
                if post_id:
                    break

print("Final Extracted post_id:", post_id)
