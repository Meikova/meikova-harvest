import requests
import re

url = "https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256/tap-1"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
resp = requests.get(url, headers=headers, verify=False, timeout=15)
html = resp.text

# 1. Search for 'T Vietsub' anywhere in HTML (case-insensitive)
matches = [m.start() for m in re.finditer(r'T Vietsub', html, re.IGNORECASE)]
print(f"Found {len(matches)} occurrences of 'T Vietsub':")
for idx, pos in enumerate(matches):
    start = max(0, pos - 150)
    end = min(len(html), pos + 150)
    snippet = html[start:end].replace('\n', ' ')
    print(f"Match {idx+1} (at index {pos}): ... {snippet} ...\n")

# 2. Search for any JSON structures or scripts containing 'server' and 'link'
# Let's write any script tags that look relevant
script_tags = re.findall(r'<script.*?>.*?</script>', html, re.DOTALL | re.IGNORECASE)
print(f"Total script tags: {len(script_tags)}")
for idx, tag in enumerate(script_tags):
    if 'server' in tag.lower() or 'link' in tag.lower() or 'vietsub' in tag.lower():
        print(f"Script {idx+1} matches (length {len(tag)}):")
        # print first 300 chars
        print(tag[:300].strip() + "\n...\n" + tag[-300:].strip())
        print("-" * 50)
