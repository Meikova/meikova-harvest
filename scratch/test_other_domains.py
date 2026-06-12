import requests
import urllib3
urllib3.disable_warnings()

path = "/player/master/1780659758220_ep135015_episode_135015"
domains = [
    "https://vip.opstream90.com",
    "https://vip.opstream10.com",
    "https://v7.kkphimplayer7.com",
    "https://player.phimapi.com",
    "https://motchilli.ac",
    "https://fcloud.live"
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

for domain in domains:
    url = domain + path
    try:
        resp = requests.get(url, headers=headers, verify=False, timeout=8)
        print(f"Domain: {domain} | Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"SUCCESS! First 200 chars of body:\n{resp.text[:200]}\n")
    except Exception as e:
        print(f"Domain: {domain} | Error: {e}")
