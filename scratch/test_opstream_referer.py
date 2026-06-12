import requests
import urllib3
urllib3.disable_warnings()

url = "https://vip.opstream90.com/20260605/33879_0038c2d2/hls/mixed.m3u8"
referers = [
    None,
    "https://motchilli.ac/",
    "https://vip.opstream90.com/",
    "https://opstream90.com/",
    "https://www.facebook.com/"
]

for ref in referers:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    if ref:
        headers["Referer"] = ref
        
    try:
        resp = requests.get(url, headers=headers, verify=False, timeout=8)
        print(f"Referer: {ref} | Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Success! Body length: {len(resp.text)}")
    except Exception as e:
        print(f"Referer: {ref} | Error: {e}")
