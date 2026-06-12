import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import app

client = app.test_client()

# Testing a URL that fails to load (non-existent domain)
url = "https://some-non-existent-domain-1234567.xyz/page/subpage"
client_id = "test_client_id"

print(f"Analyzing non-loadable URL: {url}")
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
        print("✅ SUCCESS: Non-loadable webpage fallback parsed successfully!")
        
        # Verify title and uploader are parsed from domain/URL path
        title = data.get("title")
        uploader = data.get("uploader")
        print(f"Parsed Title: '{title}'")
        print(f"Parsed Uploader: '{uploader}'")
        
        if title == "subpage" and uploader == "some-non-existent-domain-1234567.xyz":
            print("✅ SUCCESS: URL parameters parsed correctly!")
        else:
            print("❌ FAILURE: Title or uploader does not match URL path segments.")
            
        # Verify the fallback option is present
        video_options = data.get("video_options", [])
        fallback_opts = [o for o in video_options if o.get("format_id") == "generic_fallback"]
        if fallback_opts:
            print("✅ SUCCESS: Found 'generic_fallback' option pointing to page url.")
        else:
            print("❌ FAILURE: 'generic_fallback' option not found in video_options.")
    else:
        print("❌ FAILURE: API did not return success for non-loadable webpage.")
except Exception as e:
    print("Error parsing response:", e)
    print("Raw response:", response.data)
