import requests
import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

url = "http://127.0.0.1:5000/api/info"
payload = {
    # Public TikTok video from official account
    "url": "https://www.tiktok.com/@tiktok/video/7311025539656461601",
    "client_id": "client_537ngrlf0hnuty574auzds"
}

print("Querying /api/info for public TikTok video...")
try:
    r = requests.post(url, json=payload, timeout=30)
    print(f"Status Code: {r.status_code}")
    data = r.json()
    print("Response keys:", list(data.keys()))
    if data.get("status") == "success":
        print(f"Title: {data.get('title')}")
        print(f"Platform: {data.get('platform_label')} ({data.get('platform_class')})")
        print("Video Options:")
        for opt in data.get("video_options", []):
            print(f"  - {opt.get('label')} | {opt.get('resolution')} | {opt.get('size')} | Watermark: {'watermark' in opt.get('format_id', '').lower()}")
        print("Images Count:", len(data.get("images", [])))
        if data.get("images"):
            print("First image label:", data.get("images")[0].get("label"))
    else:
        print("Error:", data.get("message"))
except Exception as e:
    print(f"Error querying API: {e}")
