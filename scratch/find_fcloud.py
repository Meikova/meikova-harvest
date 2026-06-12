import requests
import re
import urllib3
urllib3.disable_warnings()

url = "https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256/tap-1"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
resp = requests.get(url, headers=headers, verify=False, timeout=15)
html = resp.text

matches = [m.start() for m in re.finditer(r'fcloud\.live', html, re.IGNORECASE)]
print(f"Found {len(matches)} occurrences of 'fcloud.live':")
for idx, pos in enumerate(matches):
    start = max(0, pos - 150)
    end = min(len(html), pos + 150)
    snippet = html[start:end].replace('\n', ' ')
    print(f"Match {idx+1}: ... {snippet} ...\n")
