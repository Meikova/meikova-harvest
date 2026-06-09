import requests

url = "http://127.0.0.1:5000/api/info"
payload = {
    "url": "https://www.facebook.com/stories/729012027223830/UzpfSVNDOjE1MzIxMzM0MDE4MzY2Mzc=/?bucket_count=9&source=story_tray",
    "client_id": "client_537ngrlf0hnuty574auzds"
}

print("Testing /api/info with Facebook Story URL...")
try:
    res = requests.post(url, json=payload, timeout=20)
    print("Status Code:", res.status_code)
    data = res.json()
    print("Status:", data.get("status"))
    if data.get("status") == "success":
        print("Title:", data.get("title"))
        print("Uploader:", data.get("uploader"))
        print("Thumbnail:", data.get("thumbnail")[:80] + "...")
        print("Video Options:")
        for idx, opt in enumerate(data.get("video_options", [])):
            print(f" {idx+1}. Label: {opt['label']}, Ext: {opt['ext']}, Format ID: {opt['format_id']}")
            print(f"    URL: {opt['url'][:80]}...")
    else:
        print("Error message:", data.get("message"))
except Exception as e:
    print("API request failed:", e)
