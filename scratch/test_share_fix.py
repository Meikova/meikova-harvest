import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import app

client = app.test_client()

url = "https://www.facebook.com/share/p/1B9Tkjw1tE/"
client_id = "client_lvnnn0l2zy8d6g9idw3j9a"

print(f"Testing API with URL: {url}")
response = client.post(
    "/api/info",
    data=json.dumps({"url": url, "client_id": client_id}),
    content_type="application/json"
)

print(f"Status Code: {response.status_code}")
try:
    data = json.loads(response.data.decode("utf-8"))
    if response.status_code == 200:
        print("✅ Success!")
        print(f"  Title:    {data.get('title')}")
        print(f"  Uploader: {data.get('uploader')}")
        print(f"  Duration: {data.get('duration')}")
        print(f"  Images:   {len(data.get('images', []))}")
        print(f"  Videos:   {len([v for v in data.get('video_options', []) if v.get('ext') == 'mp4'])}")
    else:
        print(f"❌ Error: {data.get('message')}")
except Exception as e:
    print("Error parsing response:", e)
    print("Raw response:", response.data)
