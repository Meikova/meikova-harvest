import requests
import re
import json

url = "https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256/tap-1"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
resp = requests.get(url, headers=headers, verify=False, timeout=15)
html = resp.text

# Extract all absolute URLs
urls = re.findall(r'https?://[a-zA-Z0-9./?=&_-]+', html)
unique_urls = sorted(list(set(urls)))

with open("scratch/all_urls.json", "w", encoding="utf-8") as f:
    json.dump(unique_urls, f, indent=2)

print(f"Dumped {len(unique_urls)} unique URLs to scratch/all_urls.json")
