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
    "-b", cookie_file,
]
command.append(url)

result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
html = result.stdout

share_token = "18fgW8Tbvc"
scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)

print(f"HTML length: {len(html)}")
print(f"Total scripts: {len(scripts)}")

# Find the script with share token
for i, s in enumerate(scripts):
    if share_token not in s:
        continue
    print(f"\nShare token found in script {i} (len={len(s)})")
    
    try:
        data = json.loads(s)
    except:
        print("  Failed to parse")
        continue
    
    # Find the route URL containing the share token
    def find_route(d, path=""):
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, str) and share_token in v:
                    decoded = v.replace("\\/", "/").replace("\\u00253A", ":").replace("\\u00252F", "/").replace("\\u0025", "%")
                    decoded = urllib.parse.unquote(decoded)
                    print(f"  [{path}.{k}]: {decoded}")
                    # Extract permalink
                    perm = re.search(r'/permalink/(\d+)', decoded)
                    if perm:
                        print(f"    -> PERMALINK ID: {perm.group(1)}")
                elif isinstance(v, (dict, list)):
                    find_route(v, f"{path}.{k}")
        elif isinstance(d, list):
            for idx, item in enumerate(d):
                if isinstance(item, (dict, list)):
                    find_route(item, f"{path}[{idx}]")
    
    find_route(data)
    
    # Find all post_id entries in this specific script
    post_ids_in_script = re.findall(r'"post_id"\s*:\s*"(\d+)"', s)
    print(f"\n  Post IDs in this script: {set(post_ids_in_script)}")
    break

# Now check: is the permalink ID in the HTML at all?
permalink_id = None
for i, s in enumerate(scripts):
    if share_token not in s:
        continue
    perm_matches = re.findall(r'permalink/(\d+)', s)
    if perm_matches:
        permalink_id = perm_matches[0]
        print(f"\nPermalink ID from share script: {permalink_id}")
    break

if permalink_id:
    # Check how this ID appears across ALL scripts
    for i, s in enumerate(scripts):
        if permalink_id not in s:
            continue
        # Find what keys reference this ID
        try:
            data = json.loads(s)
        except:
            continue
        
        def find_id_usage(d, path="", depth=0):
            if depth > 8: return
            if isinstance(d, dict):
                for k, v in d.items():
                    if isinstance(v, str) and permalink_id == v:
                        print(f"  Script {i}, {path}.{k} = {v}")
                    elif isinstance(v, str) and permalink_id in v and len(v) < 200:
                        print(f"  Script {i}, {path}.{k} contains: {v[:150]}")
                    elif isinstance(v, (dict, list)):
                        find_id_usage(v, f"{path}.{k}", depth+1)
            elif isinstance(d, list):
                for idx, item in enumerate(d):
                    if isinstance(item, (dict, list)):
                        find_id_usage(item, f"{path}[{idx}]", depth+1)
        
        find_id_usage(data)

# Check all progressive_urls in the entire HTML
prog_count = len(re.findall(r'"progressive_url"', html))
play_count = len(re.findall(r'"playable_url"', html))
play_hd_count = len(re.findall(r'"playable_url_quality_hd"', html))
print(f"\nprogressive_url count: {prog_count}")
print(f"playable_url count: {play_count}")
print(f"playable_url_quality_hd count: {play_hd_count}")
