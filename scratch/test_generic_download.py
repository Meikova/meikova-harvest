import sys
import os
import json
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import app
from config import downloads_status, downloads_status_lock

client = app.test_client()

url = "https://example.com"
format_id = "generic_fallback"
title = "Example Domain Webpage"
client_id = "test_client_id"

print(f"Triggering download for URL: {url} with format: {format_id}")
response = client.post(
    "/api/download",
    data=json.dumps({
        "url": url,
        "format_id": format_id,
        "title": title,
        "ext": "html",
        "client_id": client_id
    }),
    content_type="application/json"
)

print(f"Post Response Code: {response.status_code}")
data = json.loads(response.data.decode("utf-8"))
print("Post Response Data:", data)

if response.status_code == 200 and data.get("status") == "success":
    download_id = data.get("download_id")
    print(f"Successfully enqueued download! download_id: {download_id}")
    
    # Poll progress for up to 15 seconds
    completed = False
    for i in range(15):
        time.sleep(1)
        status_res = client.get(f"/api/download/status/{download_id}")
        status_data = json.loads(status_res.data.decode("utf-8"))
        print(f"Polling status [{i+1}]:", status_data)
        
        if status_data.get("status") == "complete":
            print("✅ SUCCESS: Download task completed successfully!")
            completed = True
            
            # Check if temporary folder contains the saved file
            filename = status_data.get("filename")
            temp_dir = status_data.get("temp_dir")
            if filename and temp_dir:
                filepath = os.path.join(temp_dir, filename)
                print(f"Verifying file path: {filepath}")
                if os.path.exists(filepath):
                    print("✅ SUCCESS: File exists on disk!")
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        if "Example Domain" in content:
                            print("✅ SUCCESS: File contains webpage content!")
                        else:
                            print("❌ FAILURE: File content does not match expected page content.")
                else:
                    print("❌ FAILURE: Saved file does not exist on disk.")
            break
        elif status_data.get("status") == "error":
            print("❌ FAILURE: Download task failed with error:", status_data.get("error"))
            break
            
    if not completed:
        print("❌ FAILURE: Download task timed out.")
else:
    print("❌ FAILURE: Failed to enqueue download task.")
