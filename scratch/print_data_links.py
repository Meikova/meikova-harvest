import requests
import re
import urllib3
urllib3.disable_warnings()

url = "https://phimchillhd.net/phim/giao-duc-chan-chinh/tap-1_1353070.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://phimchillhd.net/"
}

resp = requests.get(url, headers=headers, verify=False, timeout=10)
page_html = resp.text

data_link_elements = re.findall(r'<a[^>]+data-link=["\']([^"\']+)["\'][^>]*>(.*?)</a>', page_html, re.IGNORECASE | re.DOTALL)
print(f"Found {len(data_link_elements)} data-link elements:")
for idx, (link, text) in enumerate(data_link_elements):
    clean_text = re.sub(r'<[^>]+>', '', text).strip()
    print(f"  {idx+1}: text='{clean_text}' | link='{link}'")
