import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

client = app.test_client()

url = "https://phimchillhd.net/phim/giao-duc-chan-chinh_46486.html"
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
            # Safe print for Windows console
            safe_label = opt.get('label').encode('ascii', 'ignore').decode('ascii')
            safe_server = opt.get('server').encode('ascii', 'ignore').decode('ascii')
            print(f"  - Label: {safe_label}")
            print(f"    Server: {safe_server}")
            print(f"    Episode: {opt.get('episode')}")
            print(f"    URL: {opt.get('url')[:120]}...")
            print(f"    Size: {opt.get('size')}")
    else:
        print("❌ FAILED!")
        print(f"Message: {data.get('message')}")
except Exception as e:
    print("Error parsing response:", e)
    print("Raw response:", response.data)
