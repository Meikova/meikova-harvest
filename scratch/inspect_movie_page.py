import requests
import re
import json

url = "https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
resp = requests.get(url, headers=headers, verify=False)
html = resp.text
clean_html = html.replace('\\/', '/').replace('\\', '')

# Let's search for "server" objects or slugs
episode_pattern = r'\{[^{}]*"server"[^{}]*"name"[^{}]*"slug"[^{}]*"link"[^{}]*\}'
ep_matches = re.findall(episode_pattern, clean_html)
print(f"Found {len(ep_matches)} episode structures in JSON:")
for idx, ep_str in enumerate(ep_matches[:10]):
    print(f"\nMatch {idx+1}:")
    print(ep_str)

# Find all raw .m3u8 links
raw_m3u8_links = re.findall(r'https?://[^\s"\'\\<>#]+\.(?:m3u8|mp4)[^\s"\'\\<>#]*', clean_html)
print(f"\nFound {len(raw_m3u8_links)} raw m3u8/mp4 links:")
for idx, link in enumerate(raw_m3u8_links):
    print(f"{idx+1}: {link}")
