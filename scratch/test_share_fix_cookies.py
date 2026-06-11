import sys
import os
import json
import re
import urllib.parse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from config import TEMP_DOWNLOAD_DIR

url = "https://www.facebook.com/share/p/1B9Tkjw1tE/"
client_id = "client_lvnnn0l2zy8d6g9idw3j9a"

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

print(f"HTML Length: {len(html)}")

title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE)
if title_match:
    print("Page Title:", title_match.group(1))

share_token = "1B9Tkjw1tE"
script_blocks = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
print(f"Number of JSON script blocks: {len(script_blocks)}")

post_id = None
found_in_script_idx = []

for idx, script_text in enumerate(script_blocks):
    if share_token in script_text:
        found_in_script_idx.append(idx)
        print(f"\nFound share token in script {idx} (length={len(script_text)})")
        
        decoded_script = script_text.replace("\\/", "/").replace("\\u00253A", ":").replace("\\u00252F", "/").replace("\\u0025", "%")
        decoded_script = urllib.parse.unquote(decoded_script)
        
        # Print snippet of decoded_script around the token
        pos = decoded_script.find(share_token)
        start = max(0, pos - 150)
        end = min(len(decoded_script), pos + 150)
        print(f"  Snippet around token: ... {decoded_script[start:end]} ...")
        
        # Try to find target URLs
        urls_in_script = re.findall(r'"url"\s*:\s*"([^"]+)"', decoded_script)
        print(f"  Total URLs in this script block: {len(urls_in_script)}")
        for decoded_url in urls_in_script:
            if any(x in decoded_url for x in ["/posts/", "/permalink/", "/groups/", "/photos/", "/videos/"]):
                print(f"    Possible Target URL: {decoded_url}")
            
            m = re.search(r'/posts/([^/?#]+)', decoded_url)
            if m:
                post_id = m.group(1)
                print(f"    => Resolved posts ID: {post_id}")
                break
            m = re.search(r'/permalink/([^/?#]+)', decoded_url)
            if m:
                post_id = m.group(1)
                print(f"    => Resolved permalink ID: {post_id}")
                break
            m = re.search(r'/photos/[^/]+/([^/?#]+)', decoded_url)
            if m:
                post_id = m.group(1)
                print(f"    => Resolved photos ID: {post_id}")
                break
            m = re.search(r'/videos/([^/?#]+)', decoded_url)
            if m:
                post_id = m.group(1)
                print(f"    => Resolved videos ID: {post_id}")
                break
        if post_id:
            break

# If not found via share token, look for canonical_url
if not post_id:
    canonical_match = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', html) or re.search(r'<meta\s+property="og:url"\s+content="([^"]+)"', html)
    if canonical_match:
        canonical_url = canonical_match.group(1)
        print(f"Canonical URL: {canonical_url}")
        m = re.search(r'/posts/([^/?#]+)', canonical_url) or re.search(r'/permalink/([^/?#]+)', canonical_url)
        if m:
            post_id = m.group(1)
            print(f"Resolved post_id from canonical URL: {post_id}")

print("\nFinal post_id found:", post_id)
