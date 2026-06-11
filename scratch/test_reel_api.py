"""Test API endpoint for /reel/ URL to see full response."""
import requests, json, sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

url = "https://www.facebook.com/reel/769241986206453"
client_id = "client_lvnnn0l2zy8d6g9idw3j9a"

print(f"Testing: {url}")
r = requests.post("http://127.0.0.1:5000/api/info", json={"url": url, "client_id": client_id}, timeout=120)
data = r.json()

print(f"HTTP: {r.status_code}")
print(f"status: {data.get('status')}")
print(f"title: {data.get('title', 'N/A')[:150]}")
print(f"uploader: {data.get('uploader', 'N/A')}")
print(f"thumbnail: {str(data.get('thumbnail', 'N/A'))[:100]}")
print(f"duration: {data.get('duration', 'N/A')}")
print(f"upload_date: {data.get('upload_date', 'N/A')}")
print(f"views: {data.get('views', 'N/A')}")
print(f"likes: {data.get('likes', 'N/A')}")
print(f"platform_label: {data.get('platform_label', 'N/A')}")
print(f"platform_class: {data.get('platform_class', 'N/A')}")

vo = data.get("video_options", [])
print(f"\nvideo_options: {len(vo)}")
for v in vo[:5]:
    print(f"  {v.get('format_id')}: {v.get('label')} | res={v.get('resolution','?')} | size={v.get('size','?')}")
