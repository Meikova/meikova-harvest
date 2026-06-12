import requests
import urllib3
urllib3.disable_warnings()

url = "https://p16-ad-sg.ibyteimg.com/origin/ad-site-i18n/202606055d0d3570b10d016444e4b23b"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256/tap-9"
}

resp = requests.get(url, headers=headers, verify=False)
print("Hex:", resp.content.hex())
print("Length:", len(resp.content))
