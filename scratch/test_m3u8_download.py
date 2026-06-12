import sys
import os
import time
import uuid
import json
import threading
import static_ffmpeg
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

static_ffmpeg.add_paths()
print("static-ffmpeg paths injected successfully.")

sys.path.append(os.path.abspath('.'))

from tasks.download import bg_download_task, downloads_status, downloads_status_lock

# We test one of the harvested m3u8 URLs
m3u8_url = "https://vip.opstream90.com/20260605/33879_0038c2d2/index.m3u8"
client_id = "test_client_m3u8"
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

print(f"Starting bg_download_task for m3u8 with download_id: {download_id}...")

# We download only a few seconds using trim options to keep the test extremely fast (e.g. 5 seconds)
thread = threading.Thread(
    target=bg_download_task,
    args=(download_id, m3u8_url, "direct_video_1", "mp4", "192", "Test Movie Stream", client_id),
    kwargs={
        "trim_start": "00:00:00",
        "trim_end": "00:00:05",
        "translate_subs": None,
        "voiceover_active": False
    }
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
print(json.dumps(final_status, indent=2))

filepath = final_status.get("filepath")
if filepath and os.path.exists(filepath):
    print(f"\nSUCCESS! Output file exists at: {filepath}")
    print(f"File size: {os.path.getsize(filepath)} bytes")
else:
    print("\nFAILED: Output file does not exist.")
