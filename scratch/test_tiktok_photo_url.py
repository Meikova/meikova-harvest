import requests
import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

url = "http://127.0.0.1:5000/api/info"
payload = {
    "url": "https://www.tiktok.com/@mi3k_18dp/photo/7649036378268781842?is_from_webapp=1&sender_device=pc&web_id=7626642626586117640",
    "client_id": "client_537ngrlf0hnuty574auzds"
}

print("Querying /api/info for TikTok photo URL...")
try:
    r = requests.post(url, json=payload, timeout=30)
    print(f"Status Code: {r.status_code}")
    data = r.json()
    print("Response keys:", list(data.keys()))
    if data.get("status") == "success":
        print(f"Title: {data.get('title')}")
        print(f"Platform: {data.get('platform_label')} ({data.get('platform_class')})")
        print("Video Options Count:", len(data.get("video_options", [])))
        print("Images Count:", len(data.get("images", [])))
        if data.get("images"):
            print("First image label:", data.get("images")[0].get("label"))
            print("First image URL:", data.get("images")[0].get("url")[:80] + "...")
    else:
        print("Error:", data.get("message"))
except Exception as e:
    print(f"Error querying API: {e}")
