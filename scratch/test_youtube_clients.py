import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import app

client = app.test_client()

# YouTube Video ID: eBm23CzA-w4 (a standard music video/short)
url = "https://www.youtube.com/watch?v=eBm23CzA-w4"
client_id = "test_client_id"

print(f"Analyzing YouTube URL: {url} with player_client=ios,android,...")
response = client.post(
    "/api/info",
    data=json.dumps({"url": url, "client_id": client_id}),
    content_type="application/json"
)

print(f"Status Code: {response.status_code}")
try:
    data = json.loads(response.data.decode("utf-8"))
    if response.status_code == 200 and data.get("status") == "success":
        print("✅ SUCCESS: YouTube metadata parsed successfully using alternative clients!")
        print(f"Video Title: {data.get('title')}")
        print(f"Number of formats: {len(data.get('video_options', []))}")
    else:
        print("❌ FAILURE: YouTube metadata parsing failed.")
        print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print("Error parsing response:", e)
    print("Raw response:", response.data)
