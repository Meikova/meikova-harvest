import requests
import time
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# First query info to get the playUrl
info_url = "http://127.0.0.1:5000/api/info"
info_payload = {
    "url": "https://www.tiktok.com/@mi3k_18dp/photo/7649036378268781842",
    "client_id": "client_537ngrlf0hnuty574auzds"
}

print("Fetching info...")
r = requests.post(info_url, json=info_payload, timeout=30)
data = r.json()
if data.get("status") != "success":
    print("Failed to get info:", data.get("message"))
    sys.exit(1)

audio_opts = data.get("audio_options", [])
if not audio_opts:
    print("No audio options found!")
    sys.exit(1)

target_opt = audio_opts[0] # direct_audio_tiktok_slideshow
print("Target audio option:", target_opt)

# Trigger download
download_url = "http://127.0.0.1:5000/api/download"
download_payload = {
    "url": target_opt["url"],
    "format_id": target_opt["format_id"],
    "ext": "mp3",
    "quality": "192",
    "title": "Imagine Dragons - Shots Remix",
    "client_id": "client_537ngrlf0hnuty574auzds"
}

print("Triggering download...")
r = requests.post(download_url, json=download_payload, timeout=10)
download_data = r.json()
print("Download trigger response:", download_data)
if download_data.get("status") != "success":
    print("Download failed to trigger!")
    sys.exit(1)

download_id = download_data["download_id"]

# Poll status
status_url = f"http://127.0.0.1:5000/api/download/status/{download_id}"
for i in range(20):
    time.sleep(2)
    sr = requests.get(status_url)
    sdata = sr.json()
    print(f"Poll {i+1}: Status: {sdata.get('status')} | Progress: {sdata.get('progress')}% | Message: {sdata.get('message')}")
    if sdata.get("status") == "complete":
        print("DOWNLOAD COMPLETED SUCCESSFULLY!")
        break
    elif sdata.get("status") == "error":
        print("DOWNLOAD FAILED with error:", sdata.get("error"))
        break
else:
    print("Timed out waiting for download.")
