import requests
import re
import urllib3
urllib3.disable_warnings()

url = "https://embed11.streamc.xyz/embed.php?hash=95ababf8cc0e03741def85ceb800e822"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://phimchillhd.net/phim/giao-duc-chan-chinh/tap-1_1353070.html"
}

resp = requests.get(url, headers=headers, verify=False, timeout=10)
print(f"Status Code: {resp.status_code}")
html = resp.text

with open("scratch/streamc_embed.html", "w", encoding="utf-8") as f:
    f.write(html)
print("Saved HTML to scratch/streamc_embed.html")

# Find any m3u8 or mp4
m3u8s = re.findall(r'https?://[^\s"\'\\<>#]+\.(?:m3u8|mp4)[^\s"\'\\<>#]*', html)
print(f"\nFound {len(m3u8s)} stream URLs:")
for l in m3u8s:
    print(f"  - {l}")

# Search for common patterns
url_match = re.search(r'const\s+url\s*=\s*["\']([^"\']+)["\']', html)
if url_match:
    print(f"Found 'const url': {url_match.group(1)}")

src_match = re.search(r'(?:file|source|url)\s*:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', html, re.IGNORECASE)
if src_match:
    print(f"Found file/source/url match: {src_match.group(1)}")
