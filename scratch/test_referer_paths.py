import requests
import urllib3
urllib3.disable_warnings()

url = "https://p16-ad-sg.ibyteimg.com/origin/ad-site-i18n/202606055d0d894c3c9108aa411fa5eb"
referers = [
    "https://motchilli.ac/",
    "https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256/tap-1",
    "https://motchilli.ac"
]

for ref in referers:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": ref
    }
    resp = requests.head(url, headers=headers, verify=False, timeout=8)
    print(f"Referer: {ref} | Status: {resp.status_code} | Content-Length: {resp.headers.get('Content-Length')}")
