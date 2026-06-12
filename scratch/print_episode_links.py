import requests
import re
import urllib3
urllib3.disable_warnings()

url = "https://phimchillhd.net/phim/giao-duc-chan-chinh_46486.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

resp = requests.get(url, headers=headers, verify=False, timeout=15)
clean_html = resp.text

all_ep_urls = []
seen_ep_urls = set()
for match in re.findall(r'href=["\']([^"\']+(?:/tap-|/episode-|/ep-)[^"\']+)["\']', clean_html):
    from urllib.parse import urljoin
    full_ep_url = urljoin(url, match)
    if full_ep_url not in seen_ep_urls:
        seen_ep_urls.add(full_ep_url)
        all_ep_urls.append(full_ep_url)

print(f"Found {len(all_ep_urls)} episode URLs:")
for idx, ep_url in enumerate(all_ep_urls):
    print(f"  {idx+1}: {ep_url}")
