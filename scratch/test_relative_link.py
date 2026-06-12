import requests
import urllib3
urllib3.disable_warnings()

url = "https://motchilli.ac/player/master/1780659758220_ep135015_episode_135015"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256/tap-1"
}

resp = requests.get(url, headers=headers, verify=False, timeout=15)
print(f"Status code: {resp.status_code}")
print(f"Headers: {dict(resp.headers)}")
print(f"First 500 chars of body:\n{resp.text[:500]}")
