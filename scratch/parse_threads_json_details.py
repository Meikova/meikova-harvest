import requests
import json
import re
import sys

# Set stdout/stderr to UTF-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

url = "https://www.threads.net/@chipmunk.8255885/post/DZWqikzmsye"
headers = {
    "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_patched.html)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

print("Fetching threads post page...")
res = requests.get(url, headers=headers, timeout=15)
html = res.text
print("Status code:", res.status_code)

# Find all script tags
scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
print(f"Found {len(scripts)} json scripts.")

# Let's search recursively inside JSON structures for post info
def search_key(d, target_key, found_list):
    if isinstance(d, dict):
        for k, v in d.items():
            if k == target_key:
                found_list.append(v)
            if isinstance(v, (dict, list)):
                search_key(v, target_key, found_list)
    elif isinstance(d, list):
        for item in d:
            search_key(item, target_key, found_list)

found_media = []
for idx, script_text in enumerate(scripts):
    try:
        data = json.loads(script_text)
        temp_media = []
        search_key(data, "thread_items", temp_media)
        if temp_media:
            print(f"Script {idx+1} contains 'thread_items'!")
            found_media.extend(temp_media)
    except Exception as e:
        pass

if found_media:
    print(f"Found {len(found_media)} thread_items blocks!")
    with open("scratch/threads_parsed_media.json", "w", encoding="utf-8") as f:
        json.dump(found_media, f, indent=2, ensure_ascii=False)
    print("Saved thread_items to scratch/threads_parsed_media.json")
else:
    print("Could not find 'thread_items' in script tags.")
    
    # Try searching for other keys like 'image_versions2' or 'carousel_media' in all scripts
    found_images = []
    for idx, script_text in enumerate(scripts):
        try:
            data = json.loads(script_text)
            temp = []
            search_key(data, "image_versions2", temp)
            if temp:
                print(f"Script {idx+1} contains 'image_versions2'! ({len(temp)} instances)")
                found_images.extend(temp)
        except:
            pass
            
    if found_images:
        print("Found image_versions2! Preview:")
        print(json.dumps(found_images[0], indent=2)[:500])
