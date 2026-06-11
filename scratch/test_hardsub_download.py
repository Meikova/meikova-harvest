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

# We use a short test video with subtitles
url = "https://www.youtube.com/watch?v=jfIrAcTN0Jc"
client_id = "test_client_hardsub"
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

thread = threading.Thread(
    target=bg_download_task,
    args=(download_id, url, "bestvideo[height=144]+bestaudio/best", "mp4", "192", "Test Hardsub Video", client_id),
    kwargs={
        "trim_start": "00:00:00",
        "trim_end": "00:00:05",
        "translate_subs": "vi",
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
