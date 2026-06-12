import requests
import re
import urllib3
urllib3.disable_warnings()

url = "https://phimchillhd.net/phim/giao-duc-chan-chinh/tap-10_1353095.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://phimchillhd.net/"
}

resp = requests.get(url, headers=headers, verify=False, timeout=10)
page_html = resp.text

t_match = re.search(r'<title>(.*?)</title>', page_html, re.IGNORECASE)
title = t_match.group(1) if t_match else "None"
print(f"Title: {title.encode('ascii', 'ignore').decode('ascii')}")

ep_match = re.search(r'(?:Tập|Tap|Episode|Ep)\s*(\d+)', title, re.IGNORECASE)
if ep_match:
    print(f"Parsed Episode: {ep_match.group(1)}")
else:
    print("No episode matched in title.")
