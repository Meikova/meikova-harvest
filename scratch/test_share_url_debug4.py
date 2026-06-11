import sys, os, re, json, subprocess, urllib.parse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from config import TEMP_DOWNLOAD_DIR

url = "https://www.facebook.com/share/v/18fgW8Tbvc/"

cookies_dir = os.path.join(TEMP_DOWNLOAD_DIR, "cookies")
cookie_files = [f for f in os.listdir(cookies_dir) if f.startswith("cookies_")]
cookie_file = os.path.join(cookies_dir, cookie_files[0]) if cookie_files else None

command = [
    "curl", "-s", "-L",
    "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "-H", "Accept-Language: vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "-H", "Sec-Fetch-Mode: navigate",
    "-H", "Upgrade-Insecure-Requests: 1",
]
if cookie_file:
    command.extend(["-b", cookie_file])
command.append(url)

result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
html = result.stdout

scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
print(f"Total scripts: {len(scripts)}")

# Parse all scripts, find the script with post_id 2063872181207156
target_post_id = "2063872181207156"

# Strategy: walk scripts, find the node that has our target post_id as its "post_id" field,
# then extract media from that node's subtree
for i, s in enumerate(scripts):
    if target_post_id not in s:
        continue
    try:
        data = json.loads(s)
    except:
        continue
    
    # Find the dict that has "post_id": "2063872181207156"
    def find_post_node(d, depth=0):
        if isinstance(d, dict):
            if d.get("post_id") == target_post_id:
                return d
            # Also check "id" field
            if d.get("id") == target_post_id:
                return d
            for v in d.values():
                if isinstance(v, (dict, list)):
                    result = find_post_node(v, depth+1)
                    if result:
                        return result
        elif isinstance(d, list):
            for item in d:
                if isinstance(item, (dict, list)):
                    result = find_post_node(item, depth+1)
                    if result:
                        return result
        return None
    
    post_node = find_post_node(data)
    if post_node:
        print(f"\nFound post node in script {i}")
        # Check what keys the node has
        print(f"Post node keys: {list(post_node.keys())[:20]}")
        
        # Now extract all progressive_url and playable_url from this node
        video_urls = []
        image_urls = []
        def extract_media(d):
            if isinstance(d, dict):
                if "progressive_url" in d and d["progressive_url"]:
                    pu = d["progressive_url"]
                    if isinstance(pu, str) and "fbcdn.net" in pu:
                        pu = pu.replace("\\/", "/")
                        video_urls.append(pu)
                if "playable_url" in d and d["playable_url"]:
                    pu = d["playable_url"]
                    if isinstance(pu, str) and "fbcdn.net" in pu:
                        pu = pu.replace("\\/", "/")
                        video_urls.append(pu)
                if d.get("__typename") == "Photo":
                    img = d.get("viewer_image") or d.get("image")
                    if isinstance(img, dict) and img.get("uri"):
                        image_urls.append(img["uri"].replace("\\/", "/"))
                for v in d.values():
                    if isinstance(v, (dict, list)):
                        extract_media(v)
            elif isinstance(d, list):
                for item in d:
                    if isinstance(item, (dict, list)):
                        extract_media(item)
        
        extract_media(post_node)
        print(f"\nVideos from post node: {len(video_urls)}")
        for vu in video_urls:
            print(f"  {vu[:150]}...")
        print(f"\nImages from post node: {len(image_urls)}")
        for iu in image_urls:
            print(f"  {iu[:150]}...")
        break
else:
    print("Post node not found in any script")
    
# Also try a different approach: find "creation_story" that links to our post
for i, s in enumerate(scripts):
    if target_post_id not in s:
        continue
    try:
        data = json.loads(s)
    except:
        continue
    
    def find_creation_story(d, depth=0):
        results = []
        if isinstance(d, dict):
            if "creation_story" in d:
                cs = d["creation_story"]
                cs_str = json.dumps(cs)
                if target_post_id in cs_str:
                    results.append(("creation_story", d))
            if "comet_sections" in d:
                cs_str = json.dumps(d)
                if target_post_id in cs_str:
                    # Check if this has media
                    if "progressive_url" in cs_str or "playable_url" in cs_str or "viewer_image" in cs_str:
                        results.append(("comet_sections", d))
            for v in d.values():
                if isinstance(v, (dict, list)):
                    results.extend(find_creation_story(v, depth+1))
        elif isinstance(d, list):
            for item in d:
                if isinstance(item, (dict, list)):
                    results.extend(find_creation_story(item, depth+1))
        return results
    
    cs_nodes = find_creation_story(data)
    if cs_nodes:
        print(f"\n--- creation_story/comet_sections nodes in script {i}: {len(cs_nodes)} ---")
        for kind, node in cs_nodes[:3]:
            node_str = json.dumps(node)
            prog_count = node_str.count('"progressive_url"')
            play_count = node_str.count('"playable_url"')
            photo_count = node_str.count('"Photo"')
            print(f"  {kind}: progressive_url x{prog_count}, playable_url x{play_count}, Photo x{photo_count}, size={len(node_str)}")
    break
