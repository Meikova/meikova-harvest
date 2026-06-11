import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from extractors.facebook import scrape_fb_post

url = "https://www.facebook.com/share/p/1B9Tkjw1tE/"
client_id = "client_lvnnn0l2zy8d6g9idw3j9a"

res = scrape_fb_post(url, client_id)

print("Status:", res.get("status"))
print("Title:", res.get("title"))
print("Uploader:", res.get("uploader"))
print("Images count:", len(res.get("images", [])))
print("Video options count:", len(res.get("video_options", [])))

print("\n--- Video Options ---")
for o in res.get("video_options", []):
    print(f"Format ID: {o.get('format_id')}, Ext: {o.get('ext')}, Res: {o.get('resolution')}, Label: {o.get('label')}")
    # Print a snippet of url
    url_val = o.get('url', '')
    print(f"  URL: {url_val[:80]}...")
