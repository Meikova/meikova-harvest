import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

client = app.test_client()

url = "https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256"
client_id = "test_client_api"

print(f"Testing /api/info with URL: {url}")
response = client.post(
    "/api/info",
    data=json.dumps({"url": url, "client_id": client_id}),
    content_type="application/json"
)

print(f"Status Code: {response.status_code}")
data = json.loads(response.data.decode("utf-8"))

with open("scratch/api_output.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Output written to scratch/api_output.json")
