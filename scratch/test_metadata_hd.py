import sys, os, re, json, subprocess, urllib.parse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from config import TEMP_DOWNLOAD_DIR

url = "https://www.facebook.com/share/v/18fgW8Tbvc/"
cookie_file = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", "cookies_client_lvnnn0l2zy8d6g9idw3j9a.txt")

command = [
    "curl", "-s", "-L",
    "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "-H", "Accept-Language: vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "-H", "Sec-Fetch-Mode: navigate",
    "-H", "Upgrade-Insecure-Requests: 1",
    "-b", cookie_file,
]
command.append(url)

result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
html = result.stdout

print(f"HTML length: {len(html)}")

# 1. Check metadata (og tags)
og_title = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html)
og_desc = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', html)
og_image = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
title_tag = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE)

print(f"\nog:title: {og_title.group(1) if og_title else 'NOT FOUND'}")
print(f"og:description: {og_desc.group(1)[:100] if og_desc else 'NOT FOUND'}")
print(f"og:image: {og_image.group(1)[:100] if og_image else 'NOT FOUND'}")
print(f"<title>: {title_tag.group(1)[:100] if title_tag else 'NOT FOUND'}")

# 2. Find the target post node and check ALL video-related fields
post_id = "2063872181207156"
scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)

for i, s in enumerate(scripts):
    if f'"post_id":"{post_id}"' not in s and f'"post_id": "{post_id}"' not in s:
        continue
    try:
        data = json.loads(s)
    except:
        continue
    
    def find_post_node(d):
        if isinstance(d, dict):
            if d.get("post_id") == post_id:
                return d
            for v in d.values():
                if isinstance(v, (dict, list)):
                    r = find_post_node(v)
                    if r: return r
        elif isinstance(d, list):
            for item in d:
                if isinstance(item, (dict, list)):
                    r = find_post_node(item)
                    if r: return r
        return None
    
    post_node = find_post_node(data)
    if not post_node:
        continue
    
    print(f"\n{'='*60}")
    print(f"Found post node in script {i}")
    
    # Extract ALL video-related fields
    video_fields = {}
    def find_video_fields(d, path=""):
        if isinstance(d, dict):
            for k in ["playable_url", "playable_url_quality_hd", "progressive_url", 
                       "browser_native_hd_url", "browser_native_sd_url",
                       "playable_url_dash", "width", "height", "original_width", "original_height"]:
                if k in d and d[k]:
                    val = d[k]
                    if isinstance(val, str) and len(val) > 100:
                        val = val[:100] + "..."
                    video_fields[f"{path}.{k}"] = val
            
            # Check for __typename == Video
            if d.get("__typename") == "Video":
                print(f"\n  Video node at {path}:")
                print(f"    id: {d.get('id', 'N/A')}")
                for vk in ["playable_url", "playable_url_quality_hd", "progressive_url",
                            "browser_native_hd_url", "browser_native_sd_url", "width", "height"]:
                    if vk in d:
                        val = d[vk]
                        if isinstance(val, str) and len(val) > 120:
                            val = val[:120] + "..."
                        print(f"    {vk}: {val}")
                        
            for k, v in d.items():
                if isinstance(v, (dict, list)):
                    find_video_fields(v, f"{path}.{k}")
        elif isinstance(d, list):
            for idx, item in enumerate(d):
                if isinstance(item, (dict, list)):
                    find_video_fields(item, f"{path}[{idx}]")
    
    find_video_fields(post_node)
    
    # Also check for title/description in the post node
    print(f"\n{'='*60}")
    print("Metadata from post node:")
    
    def find_text_content(d, path="", depth=0):
        if depth > 15:
            return
        if isinstance(d, dict):
            # Look for message/text fields
            if "message" in d and isinstance(d["message"], dict):
                msg = d["message"]
                if "text" in msg:
                    print(f"  message.text at {path}: {str(msg['text'])[:200]}")
            if "name" in d and isinstance(d["name"], str) and len(d["name"]) > 3:
                print(f"  name at {path}: {d['name']}")
            if "actors" in d and isinstance(d["actors"], list):
                for actor in d["actors"]:
                    if isinstance(actor, dict) and "name" in actor:
                        print(f"  actor.name at {path}: {actor['name']}")
            for k, v in d.items():
                if isinstance(v, (dict, list)):
                    find_text_content(v, f"{path}.{k}", depth+1)
        elif isinstance(d, list):
            for idx, item in enumerate(d):
                if isinstance(item, (dict, list)):
                    find_text_content(item, f"{path}[{idx}]", depth+1)
    
    find_text_content(post_node)
    break
