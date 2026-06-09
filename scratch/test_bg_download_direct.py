import sys
import os
import time
sys.path.append(os.path.abspath('.'))

from app import bg_download_task, downloads_status, downloads_status_lock
import uuid

url = "https://www.facebook.com/FuzeTeaVN/videos/1305800194990596/?rdid=MPAnduUW537wyGJ4#"
client_id = "client_537ngrlf0hnuty574auzds"
download_id = str(uuid.uuid4())

# Initialize status
with downloads_status_lock:
    downloads_status[download_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Queued. Starting download...",
        "ext": "mp4",
        "filepath": None,
        "temp_dir": None,
        "filename": None,
        "error": None,
    }

print(f"Starting bg_download_task with download_id: {download_id}...")

import threading
thread = threading.Thread(
    target=bg_download_task,
    args=(download_id, url, "bestvideo+bestaudio/best", "mp4", "192", "FUZE TEA on Reels", client_id)
)
thread.start()

# Poll status
print("Polling status...")
last_message = ""
while thread.is_alive():
    with downloads_status_lock:
        status = downloads_status.get(download_id, {})
    
    current_status = status.get("status")
    progress = status.get("progress")
    message = status.get("message")
    
    status_str = f"Status: {current_status} | Progress: {progress}% | Message: {message}"
    if status_str != last_message:
        print(status_str)
        last_message = status_str
        
    time.sleep(1)

thread.join()

with downloads_status_lock:
    final_status = downloads_status.get(download_id, {})
print("\nFinal Status:")
import json
print(json.dumps(final_status, indent=2))
