import os
import sys
sys.path.append(os.getcwd())

import json
from app import app, TEMP_DOWNLOAD_DIR

# List files in downloads/cookies
cookies_dir = os.path.join(TEMP_DOWNLOAD_DIR, "cookies")
print("Cookies directory:", cookies_dir)
if os.path.exists(cookies_dir):
    print("Files in cookies dir:", os.listdir(cookies_dir))
else:
    print("Cookies directory does not exist")

# Find the latest cookie file if any
cookie_files = [f for f in os.listdir(cookies_dir) if f.startswith("cookies_")] if os.path.exists(cookies_dir) else []
client_id = None
if cookie_files:
    # Get client_id from filename e.g. cookies_client_xxx.txt
    filename = cookie_files[0]
    client_id = filename.replace("cookies_", "").replace(".txt", "")
    print("Using client_id:", client_id)

url = "https://www.reddit.com/r/ArtificialInteligence/s/bX7TYEv45P"
client = app.test_client()
response = client.post('/api/info', json={
    "url": url,
    "client_id": client_id
})

print("Status code:", response.status_code)
try:
    data = json.loads(response.data)
    print("Thumbnail returned:", data.get("thumbnail"))
    print("Uploader:", data.get("uploader"))
    print("Title:", data.get("title"))
    print("Video Options Count:", len(data.get("video_options", [])))
    print("Audio Options Count:", len(data.get("audio_options", [])))
    print("Images count:", len(data.get("images", [])))
    if data.get("images"):
        print("First Image URL:", data.get("images")[0].get("url"))
except Exception as e:
    print("Error parsing response:", e)
    print("Raw response:", response.data[:2000])
