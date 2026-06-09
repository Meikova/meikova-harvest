import urllib.request
import json
import sys

# Reconfigure stdout to use UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

url = "http://127.0.0.1:5000/api/info"
test_url = "https://www.instagram.com/p/DZPFApnkxXR/"
client_id = "client_537ngrlf0hnuty574auzds"

data = json.dumps({
    "url": test_url,
    "client_id": client_id
}).encode("utf-8")

req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req) as res:
        response_data = json.loads(res.read().decode("utf-8"))
        print("Success! Status Code: 200")
        print("Title:", response_data.get("title"))
        print("Likes:", response_data.get("likes"))
        print("Views:", response_data.get("views"))
        print("Upload Date:", response_data.get("upload_date"))
        print("Images count:", len(response_data.get("images", [])))
        print("Video options count:", len(response_data.get("video_options", [])))
except Exception as e:
    if hasattr(e, "read"):
        print("Failed:", e.read().decode("utf-8"))
    else:
        print("Failed:", e)
