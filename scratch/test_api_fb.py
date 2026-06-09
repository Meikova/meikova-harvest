import requests
import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

url = "http://127.0.0.1:5000/api/info"
payload = {
    "url": "https://www.facebook.com/share/p/18KCdDUac7/",
    "client_id": "client_537ngrlf0hnuty574auzds"
}

print("Querying /api/info for public Facebook post...")
try:
    r = requests.post(url, json=payload, timeout=20)
    print(f"Status Code: {r.status_code}")
    data = r.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error querying API: {e}")
