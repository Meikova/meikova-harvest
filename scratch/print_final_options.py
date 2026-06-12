import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app

client = app.test_client()
url = "https://phimchillhd.net/phim/giao-duc-chan-chinh_46486.html"

response = client.post(
    "/api/info",
    data=json.dumps({"url": url, "client_id": "test"}),
    content_type="application/json"
)

data = json.loads(response.data.decode("utf-8"))
if response.status_code == 200 and data.get("status") == "success":
    video_options = data.get("video_options", [])
    print(f"Total options: {len(video_options)}")
    for idx, opt in enumerate(video_options):
        print(f"Option {idx+1}:")
        print(f"  label:   '{opt.get('label')}'")
        print(f"  server:  '{opt.get('server')}'")
        print(f"  episode: '{opt.get('episode')}'")
        print(f"  url:     '{opt.get('url')}'")
        print(f"  size:    '{opt.get('size')}'")
else:
    print("Error:", data)
