import re
import json

with open("scratch/fb_externalhit.html", "r", encoding="utf-8") as f:
    html = f.read()

scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)

def search_keys(d, target_keys, path=""):
    if isinstance(d, dict):
        for k, v in d.items():
            new_path = f"{path}.{k}" if path else k
            if k in target_keys:
                print(f"\nFound {k} at: {new_path}")
                # Print a small summary
                if isinstance(v, list):
                    print(f"List length: {len(v)}")
                    if len(v) > 0:
                        print(f"First element type: {type(v[0])}")
                        if isinstance(v[0], dict):
                            print(f"First element keys: {list(v[0].keys())}")
                elif isinstance(v, dict):
                    print(f"Dict keys: {list(v.keys())}")
                else:
                    print(f"Value: {v}")
            if isinstance(v, (dict, list)):
                search_keys(v, target_keys, new_path)
    elif isinstance(d, list):
        for idx, item in enumerate(d):
            new_path = f"{path}[{idx}]"
            if isinstance(item, (dict, list)):
                search_keys(item, target_keys, new_path)

print("Searching for attachments/subattachments...")
for idx, script_text in enumerate(scripts):
    try:
        data = json.loads(script_text)
        search_keys(data, ["attachments", "subattachments", "all_subattachments", "media_gallery_attachments"])
    except:
        pass
