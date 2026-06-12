import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import app

client = app.test_client()

# Phimchill series overview URL (from user's screenshot)
url = "https://phimchillhd.net/phim/giao-duc-chan-chinh_46486.html"
client_id = "test_client_id"

print(f"Analyzing overview URL: {url}")
response = client.post(
    "/api/info",
    data=json.dumps({"url": url, "client_id": client_id}),
    content_type="application/json"
)

print(f"Status Code: {response.status_code}")
try:
    data = json.loads(response.data.decode("utf-8"))
    if response.status_code == 200 and data.get("status") == "success":
        print("✅ SUCCESS: Overview page parsed successfully!")
        
        video_options = data.get("video_options", [])
        print(f"Total options found: {len(video_options)}")
        
        # Group options by episode
        episodes = set()
        for opt in video_options:
            ep = opt.get("episode")
            if ep:
                episodes.add(ep)
                
        print(f"Parsed episodes list: {sorted(list(episodes), key=int)}")
        
        if len(episodes) > 1:
            print("✅ SUCCESS: Correctly parsed multiple episodes from overview page!")
        else:
            print("❌ FAILURE: Only parsed one episode.")
    else:
        print("❌ FAILURE: API did not return success status.")
        print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print("Error parsing response:", e)
    print("Raw response:", response.data)
