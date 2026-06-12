import sys
import os
import requests
import re
import urllib3
urllib3.disable_warnings()

# We get a fresh streamc URL by querying the API
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app
client = app.test_client()
url = "https://phimchillhd.net/phim/giao-duc-chan-chinh_46486.html"
response = client.post("/api/info", data=json.dumps({"url": url, "client_id": "test"}), content_type="application/json")
data = json.loads(response.data.decode("utf-8"))

embed_url = None
for opt in data.get("video_options", []):
    if "streamc.xyz" in opt.get("url", ""):
        embed_url = opt.get("url")
        break

if not embed_url:
    print("No streamc embed URL found.")
    sys.exit(0)

print(f"Fetching streamc embed URL: {embed_url}")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://phimchillhd.net/"
}

resp = requests.get(embed_url, headers=headers, verify=False, timeout=10)
print(f"Status Code: {resp.status_code}")

with open("scratch/streamc_player.html", "w", encoding="utf-8") as f:
    f.write(resp.text)
print("Saved streamc player page to scratch/streamc_player.html")

# Look for data-obf or other script fields
obf = re.search(r'data-obf=["\']([^"\']+)["\']', resp.text)
if obf:
    print("Found data-obf:", obf.group(1)[:50] + "...")
else:
    print("data-obf NOT found.")
    
# Print all script tags or key configs
scripts = re.findall(r'<script[^>]*>(.*?)</script>', resp.text, re.DOTALL)
print(f"Found {len(scripts)} scripts.")
for idx, s in enumerate(scripts):
    if "player" in s or "play" in s or "config" in s or "setup" in s:
        print(f"\n--- Script {idx+1} (length {len(s)}): ---")
        print(s[:500])
