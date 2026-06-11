import sys
import os
import re
import json
import subprocess
import urllib.parse
import html as html_lib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Let's inspect the specific post from the user
url = "https://www.facebook.com/share/v/18fgW8Tbvc/"
client_id = "client_lvnnn0l2zy8d6g9idw3j9a"

TEMP_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "downloads")
client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")

command = [
    "curl",
    "-s",
    "-L",
    "-b", client_cookies,
    "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "-H", "Accept-Language: vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "-H", "Sec-Fetch-Mode: navigate",
    "-H", "Upgrade-Insecure-Requests: 1",
    url
]

print("Fetching page using curl...")
result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
html = result.stdout
print("HTML length:", len(html))

canonical_match = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', html) or re.search(r'<meta\s+property="og:url"\s+content="([^"]+)"', html)
canonical_url = canonical_match.group(1) if canonical_match else url
print("Canonical URL:", canonical_url)

post_id = None
for target_url in [canonical_url, url]:
    if post_id:
        break
    m = re.search(r'/posts/([^/?#]+)', target_url)
    if m:
        post_id = m.group(1)
        continue
    m = re.search(r'story_fbid=([^&#]+)', target_url)
    if m:
        post_id = m.group(1)
        continue
    m = re.search(r'/permalink/([^/?#]+)', target_url)
    if m:
        post_id = m.group(1)
        continue

print("Extracted post ID:", post_id)

scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
print("Scripts found:", len(scripts))

video_options = []
images = []
added_image_filenames = set()
added_video_urls = set()

def extract_filename(url_str):
    try:
        path = urllib.parse.urlparse(url_str).path
        return os.path.basename(path)
    except:
        return url_str

def search_graphql(d):
    if isinstance(d, dict):
        if "all_subattachments" in d:
            sub = d["all_subattachments"]
            if isinstance(sub, dict) and "nodes" in sub:
                nodes = sub["nodes"]
                if isinstance(nodes, list):
                    for node in nodes:
                        media = node.get("media")
                        if isinstance(media, dict):
                            viewer_img = media.get("viewer_image") or media.get("image")
                            if isinstance(viewer_img, dict) and viewer_img.get("uri"):
                                uri = viewer_img["uri"].replace("\\/", "/").replace("\\u0025", "%")
                                uri = urllib.parse.unquote(uri)
                                filename = extract_filename(uri)
                                if filename not in added_image_filenames:
                                    added_image_filenames.add(filename)
                                    images.append({
                                        "label": f"Photo {len(images)+1}",
                                        "url": uri,
                                        "ext": "jpg"
                                    })
        
        if d.get("__typename") == "Photo" or "viewer_image" in d:
            v_img = d.get("viewer_image")
            if isinstance(v_img, dict) and v_img.get("uri"):
                uri = v_img["uri"].replace("\\/", "/").replace("\\u0025", "%")
                uri = urllib.parse.unquote(uri)
                filename = extract_filename(uri)
                if filename not in added_image_filenames:
                    added_image_filenames.add(filename)
                    images.append({
                        "label": f"Photo {len(images)+1}",
                        "url": uri,
                        "ext": "jpg"
                    })
            else:
                img = d.get("image")
                if isinstance(img, dict) and img.get("uri"):
                    uri = img["uri"].replace("\\/", "/").replace("\\u0025", "%")
                    uri = urllib.parse.unquote(uri)
                    filename = extract_filename(uri)
                    if filename not in added_image_filenames:
                        added_image_filenames.add(filename)
                        images.append({
                            "label": f"Photo {len(images)+1}",
                            "url": uri,
                            "ext": "jpg"
                        })
                        
        if "playable_url" in d or "progressive_url" in d:
            playable = d.get("playable_url") or d.get("progressive_url")
            if playable and isinstance(playable, str) and "fbcdn.net" in playable:
                playable = playable.replace("\\/", "/").replace("\\u0025", "%")
                playable = urllib.parse.unquote(playable)
                if not any(x in playable.lower() for x in ["dash_baseline", "_nc_vs", "dash_prefetch"]):
                    res = "HD" if "quality_hd" in playable.lower() else "SD"
                    label = f"Facebook Video ({res})"
                    opt = {
                        "format_id": f"direct_video_{len(video_options)+1}",
                        "ext": "mp4",
                        "resolution": res,
                        "size": "Unknown Size",
                        "label": label,
                        "url": playable
                    }
                    if playable not in added_video_urls:
                        added_video_urls.add(playable)
                        video_options.append(opt)
                        
        for v in d.values():
            if isinstance(v, (dict, list)):
                search_graphql(v)
    elif isinstance(d, list):
        for item in d:
            if isinstance(item, (dict, list)):
                search_graphql(item)

# Parse main post scripts
parsed_main_scripts = []
for script_text in scripts:
    try:
        data = json.loads(script_text)
        parsed_main_scripts.append(data)
    except:
        pass

target_nodes = []
def locate_target_nodes(d):
    if isinstance(d, dict):
        is_target = False
        if post_id:
            for k, v in d.items():
                if isinstance(v, str) and post_id in v:
                    if k in ["wwwURL", "url", "share_link"] or "story" in k or "node" in k:
                        is_target = True
                        break
        if is_target:
            target_nodes.append(d)
        else:
            for v in d.values():
                if isinstance(v, (dict, list)):
                    locate_target_nodes(v)
    elif isinstance(d, list):
        for item in d:
            locate_target_nodes(item)

for data in parsed_main_scripts:
    locate_target_nodes(data)

if target_nodes:
    print(f"Targeted story matching post ID '{post_id}' found. Extracting only target media.")
    for node in target_nodes:
        search_graphql(node)
else:
    print("No target nodes found, globally scanning main post...")
    for data in parsed_main_scripts:
        search_graphql(data)

print(f"\nFinal Extracted Images: {len(images)}")
for i, img in enumerate(images):
    print(f"  Photo {i+1}: {img['url'][:120]}...")
print(f"Final Extracted Videos: {len(video_options)}")
for i, opt in enumerate(video_options):
    print(f"  Video {i+1}: {opt['label']} - {opt['url'][:120]}...")
