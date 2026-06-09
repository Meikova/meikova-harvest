import json

with open("scratch/tiktok_info.json", "r", encoding="utf-8") as f:
    info = json.load(f)

print("Searching for ALL URL strings in the JSON file...")

def search_urls(data, path=""):
    urls = []
    if isinstance(data, dict):
        for k, v in data.items():
            urls.extend(search_urls(v, f"{path}.{k}" if path else k))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            urls.extend(search_urls(item, f"{path}[{idx}]"))
    elif isinstance(data, str):
        if data.startswith("http"):
            urls.append((path, data))
    return urls

all_found = search_urls(info)
print(f"Total urls found: {len(all_found)}")
for path, url in all_found:
    print(f"Path: {path}")
    print(f"  URL: {url[:100]}...")
