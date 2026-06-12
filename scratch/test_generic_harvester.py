import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import app

client = app.test_client()

# Testing a completely generic website (should fallback cleanly instead of throwing error)
url = "https://example.com"
client_id = "test_client_id"

print(f"Analyzing generic URL: {url}")
response = client.post(
    "/api/info",
    data=json.dumps({"url": url, "client_id": client_id}),
    content_type="application/json"
)

print(f"Status Code: {response.status_code}")
try:
    data = json.loads(response.data.decode("utf-8"))
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    if response.status_code == 200 and data.get("status") == "success":
        print("✅ SUCCESS: Webpage fallback parsed successfully!")
        
        # Verify the fallback option is present
        video_options = data.get("video_options", [])
        fallback_opts = [o for o in video_options if o.get("format_id") == "generic_fallback"]
        if fallback_opts:
            print("✅ SUCCESS: Found 'generic_fallback' option pointing to page url.")
        else:
            print("❌ FAILURE: 'generic_fallback' option not found in video_options.")
    else:
        print("❌ FAILURE: API did not return success for generic website.")
except Exception as e:
    print("Error parsing response:", e)
    print("Raw response:", response.data)
