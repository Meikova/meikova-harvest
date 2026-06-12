import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

client = app.test_client()
url = "https://phimchillhd.net/phim/giao-duc-chan-chinh_46486.html"
client_id = "test_client_id"

response = client.post(
    "/api/info",
    data=json.dumps({"url": url, "client_id": client_id}),
    content_type="application/json"
)

data = json.loads(response.data.decode("utf-8"))
if response.status_code == 200 and data.get("status") == "success":
    video_options = data.get("video_options", [])
    print(f"Total options: {len(video_options)}")
    for opt in video_options:
        print(f"Option: {opt.get('label')} | Size: {opt.get('size')} | URL: {opt.get('url')[:60]}...")
else:
    print("Error:", data)
