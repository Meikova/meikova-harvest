import urllib.request
import json
import time
import sys

# Reconfigure stdout to use UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

client_id = "client_537ngrlf0hnuty574auzds"
url_info = "http://127.0.0.1:5000/api/info"
url_download = "http://127.0.0.1:5000/api/download"
url_status_prefix = "http://127.0.0.1:5000/api/download/status/"

# Step 1: Fetch metadata
print("Step 1: Fetching metadata for Instagram post...")
data_info = json.dumps({
    "url": "https://www.instagram.com/p/DZPFApnkxXR/",
    "client_id": client_id
}).encode("utf-8")

req_info = urllib.request.Request(url_info, data=data_info, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req_info) as res:
        info = json.loads(res.read().decode("utf-8"))
except Exception as e:
    print("Failed to fetch info:", e)
    sys.exit(1)

video_opts = info.get("video_options", [])
if not video_opts:
    print("No formats found in metadata response!")
    sys.exit(1)

target_opt = video_opts[0]
print(f"Target format: {target_opt['label']} ({target_opt['format_id']}) -> {target_opt['url'][:60]}...")

# Step 2: Trigger download
print("\nStep 2: Triggering download...")
data_download = json.dumps({
    "url": target_opt["url"], # The direct image URL
    "format_id": target_opt["format_id"],
    "ext": target_opt["ext"],
    "title": info["title"],
    "client_id": client_id
}).encode("utf-8")

req_download = urllib.request.Request(url_download, data=data_download, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req_download) as res:
        download_resp = json.loads(res.read().decode("utf-8"))
except Exception as e:
    print("Failed to trigger download:", e)
    sys.exit(1)

if download_resp.get("status") != "success":
    print("Trigger download returned error:", download_resp)
    sys.exit(1)

download_id = download_resp["download_id"]
print(f"Download enqueued. ID: {download_id}")

# Step 3: Poll status
print("\nStep 3: Polling status...")
url_status = url_status_prefix + download_id
last_msg = ""
while True:
    try:
        res = urllib.request.urlopen(url_status)
        status_data = json.loads(res.read().decode("utf-8"))
    except Exception as e:
        print("Polling error:", e)
        time.sleep(1)
        continue
        
    status = status_data.get("status")
    progress = status_data.get("progress")
    msg = status_data.get("message")
    
    status_str = f"Status: {status} | Progress: {progress}% | Message: {msg}"
    if status_str != last_msg:
        print(status_str)
        last_msg = status_str
        
    if status in ["complete", "error"]:
        break
        
    time.sleep(1)

print("\nFinished!")
