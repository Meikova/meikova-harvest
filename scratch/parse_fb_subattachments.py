import re
import json
import urllib.parse

with open("scratch/fb_externalhit.html", "r", encoding="utf-8") as f:
    html = f.read()

scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)

subattachments_found = []

def search_subattachments(d):
    if isinstance(d, dict):
        if "all_subattachments" in d:
            sub = d["all_subattachments"]
            if isinstance(sub, dict) and "nodes" in sub:
                nodes = sub["nodes"]
                if isinstance(nodes, list) and len(nodes) > 0:
                    subattachments_found.append(nodes)
        for v in d.values():
            if isinstance(v, (dict, list)):
                search_subattachments(v)
    elif isinstance(d, list):
        for item in d:
            if isinstance(item, (dict, list)):
                search_subattachments(item)

for script_text in scripts:
    try:
        data = json.loads(script_text)
        search_subattachments(data)
    except:
        pass

print(f"Found {len(subattachments_found)} all_subattachments structures.")
for idx, nodes in enumerate(subattachments_found):
    print(f"\nStructure [{idx+1}] nodes count: {len(nodes)}")
    for node_idx, node in enumerate(nodes):
        media = node.get("media")
        if isinstance(media, dict):
            typename = media.get("__typename")
            media_id = media.get("id")
            
            # Extract image URLs
            viewer_img = media.get("viewer_image") or media.get("image")
            img_uri = None
            if isinstance(viewer_img, dict):
                img_uri = viewer_img.get("uri")
            
            # Check other image sizes
            image_sizes = []
            if "image" in media and isinstance(media["image"], dict) and media["image"].get("uri"):
                image_sizes.append(media["image"]["uri"])
            
            print(f"  Node [{node_idx+1}] type={typename} id={media_id} uri={img_uri.split('?')[0] if img_uri else 'None'}")
