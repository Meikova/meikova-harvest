import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

client = app.test_client()

url = "https://motchilltv.lt/episodes/bai-hoc-dang-doi-tap-1/"
client_id = "test-client-id"

print(f"Sending POST request to /api/info with URL: {url}")
response = client.post(
    "/api/info",
    data=json.dumps({"url": url, "client_id": client_id}),
    content_type="application/json"
)

print(f"Status Code: {response.status_code}")
try:
    data = json.loads(response.data.decode("utf-8"))
    if response.status_code == 200:
        print("✅ SUCCESS!")
        print(f"Title: {data.get('title')}")
        print("Video options returned:")
        for opt in data.get('video_options', []):
            print(f"  - Label: {opt.get('label')}")
            print(f"    Server: {opt.get('server')}")
            print(f"    Episode: {opt.get('episode')}")
            print(f"    URL: {opt.get('url')}")
            print(f"    Size: {opt.get('size')}")
    else:
        print("❌ FAILED!")
        print(f"Message: {data.get('message')}")
except Exception as e:
    print("Error parsing response:", e)
    print("Raw response:", response.data)
