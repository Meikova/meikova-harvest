import re
import json

with open("scratch/fb_externalhit.html", "r", encoding="utf-8") as f:
    html = f.read()

scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)

photo_id = "122139628731129808"

def print_structure(d, path=""):
    if isinstance(d, dict):
        for k, v in d.items():
            new_path = f"{path}.{k}" if path else k
            if str(v) == photo_id:
                print(f"Found photo_id at path: {new_path}")
                print(f"Parent keys: {list(d.keys())}")
            if isinstance(v, (dict, list)):
                print_structure(v, new_path)
    elif isinstance(d, list):
        for idx, item in enumerate(d):
            new_path = f"{path}[{idx}]"
            if str(item) == photo_id:
                print(f"Found photo_id at path: {new_path}")
            if isinstance(item, (dict, list)):
                print_structure(item, new_path)

for idx, script_text in enumerate(scripts):
    try:
        data = json.loads(script_text)
        print_structure(data, f"script_{idx}")
    except:
        pass
