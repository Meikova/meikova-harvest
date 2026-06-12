import sys
import os
import uuid
import threading
import time
import json
import static_ffmpeg

static_ffmpeg.add_paths()
sys.path.append(os.path.abspath('.'))

from tasks.download import bg_download_task, downloads_status, downloads_status_lock

# We run a small HLS download (only 5 seconds) to test the naming logic
url = "https://fcloud.live/player/master/1780659930603_ep135023_episode_135023"
client_id = "test_naming_client"
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

print(f"Starting naming test task {download_id}...")

# Start bg_download_task with specific episode and server
thread = threading.Thread(
    target=bg_download_task,
    args=(download_id, url, "direct_video_39", "mp4", "192", "Phim Bài Học Đáng Đời Vietsub - Motchill", client_id),
    kwargs={
        "trim_start": "00:00:00",
        "trim_end": "00:00:05",
        "translate_subs": None,
        "voiceover_active": False,
        "episode": "Tập 09",
        "server": "Server: T Vietsub #1 [M3U8]"
    }
)
thread.start()

# Wait for completion
while thread.is_alive():
    time.sleep(0.5)

with downloads_status_lock:
    final_status = downloads_status.get(download_id, {})

print("\nNaming Test Result:")
print(f"Generated filename: {final_status.get('filename')}")
print(f"Output filepath exists: {os.path.exists(final_status.get('filepath', ''))}")
print(f"Full details:\n{json.dumps(final_status, indent=2)}")
