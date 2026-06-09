import re
import json
import urllib.parse

with open("scratch/fb_externalhit.html", "r", encoding="utf-8") as f:
    html = f.read()

# Find all JSON scripts
scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)

images = []
def search_viewer_images(d):
    if isinstance(d, dict):
        # Look for viewer_image or image inside Photo structure
        if d.get("__typename") == "Photo" or "viewer_image" in d:
            v_img = d.get("viewer_image")
            if isinstance(v_img, dict) and v_img.get("uri"):
                uri = v_img["uri"].replace("\\/", "/").replace("\\u0025", "%")
                uri = urllib.parse.unquote(uri)
                if uri not in images:
                    images.append(uri)
            else:
                img = d.get("image")
                if isinstance(img, dict) and img.get("uri"):
                    uri = img["uri"].replace("\\/", "/").replace("\\u0025", "%")
                    uri = urllib.parse.unquote(uri)
                    if uri not in images:
                        images.append(uri)
        for v in d.values():
            search_viewer_images(v)
    elif isinstance(d, list):
        for item in d:
            search_viewer_images(item)

for script_text in scripts:
    try:
        data = json.loads(script_text)
        search_viewer_images(data)
    except:
        pass

print(f"Found {len(images)} viewer/photo image URLs:")
for idx, img in enumerate(images):
    print(f"[{idx+1}] {img.split('?')[0]}")
