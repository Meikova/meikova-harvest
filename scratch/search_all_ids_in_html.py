import sys
import os
import json
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

url = "https://www.facebook.com/share/p/1B9Tkjw1tE/"

# Request WITHOUT cookies
command = [
    "curl", "-s", "-L",
    "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "-H", "Accept-Language: vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    url
]

import subprocess
res = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
html = res.stdout

print("HTML Length (No Cookies):", len(html))
title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE)
if title_match:
    print("Page Title:", title_match.group(1))

# Check for script application/json count
script_blocks = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
print(f"Number of JSON script blocks: {len(script_blocks)}")

# If there are scripts, let's look for share_token in them
share_token = "1B9Tkjw1tE"
found_token_count = 0
for idx, script_text in enumerate(script_blocks):
    if share_token in script_text:
        found_token_count += 1
        print(f"Found share token in script {idx} (length={len(script_text)})")
        # Print a snippet around the share token
        pos = script_text.find(share_token)
        start = max(0, pos - 150)
        end = min(len(script_text), pos + 150)
        print(f"  Snippet: ... {script_text[start:end]} ...")

# Look for any permalinks, post ids or other patterns
print("\n=== Scanning for posts/permalink URLs ===")
for idx, script_text in enumerate(script_blocks):
    urls = re.findall(r'"url"\s*:\s*"([^"]+)"', script_text)
    for u in urls:
        u_dec = u.replace("\\/", "/")
        if any(x in u_dec for x in ["/posts/", "/permalink/", "/groups/", "/photos/"]):
            print(f"  [Script {idx}] URL: {u_dec}")
