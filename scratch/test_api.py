import requests, json, sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

url = "https://www.facebook.com/share/v/18fgW8Tbvc/"
client_id = "client_lvnnn0l2zy8d6g9idw3j9a"

r = requests.post("http://127.0.0.1:5000/api/info", json={"url": url, "client_id": client_id}, timeout=120)
data = r.json()

print(f"HTTP Status: {r.status_code}")
print(f"status: {data.get('status', 'N/A')}")
print(f"title: {data.get('title', 'N/A')[:150]}")
print(f"uploader: {data.get('uploader', 'N/A')}")
print(f"thumbnail: {'YES' if data.get('thumbnail') else 'NO'}")
print(f"duration: {data.get('duration', 'N/A')}")

vo = data.get("video_options", [])
print(f"\nvideo_options: {len(vo)}")
for v in vo:
    print(f"  {v['format_id']}: {v['label']} | res={v.get('resolution','?')} | size={v.get('size','?')}")

ao = data.get("audio_options", [])
print(f"\naudio_options: {len(ao)}")

imgs = data.get("images", [])
print(f"images: {len(imgs)}")

if data.get("message"):
    print(f"\nError message: {data['message']}")
