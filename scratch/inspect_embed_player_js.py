import requests
import urllib3
urllib3.disable_warnings()

url = "https://embed11.streamc.xyz/player.js?ver=1.1"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://embed11.streamc.xyz/embed.php?hash=95ababf8cc0e03741def85ceb800e822"
}

resp = requests.get(url, headers=headers, verify=False, timeout=10)
print(f"Status Code: {resp.status_code}")
with open("scratch/player.js", "w", encoding="utf-8") as f:
    f.write(resp.text)
print("Saved player.js to scratch/player.js")
