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

share_token = "18fgW8Tbvc"

# Find the script containing our share token and parse it
for i, s in enumerate(scripts):
    if share_token not in s:
        continue
    print(f"Script {i} contains share token (length={len(s)})")
    try:
        data = json.loads(s)
    except:
        print("  Failed to parse JSON")
        continue
    
    # Search for the story node containing the share token
    def find_story_with_share(d, path=""):
        results = []
        if isinstance(d, dict):
            # Check if this dict has our share token somewhere in its values
            json_str = json.dumps(d)
            if share_token not in json_str:
                return results
                
            # Check if this is a story/node with playable_url
            if "playable_url" in d:
                pu = d.get("playable_url", "")
                if pu and isinstance(pu, str):
                    print(f"  Found playable_url at {path}: {pu[:120]}...")
                    results.append(d)
                    
            # Check for creation_story or story_node
            if d.get("__typename") in ["Story", "VideoStory", "Video"]:
                print(f"  Found {d.get('__typename')} at {path}")
                if "id" in d:
                    print(f"    ID: {d['id']}")
                results.append(d)
                    
            for k, v in d.items():
                if isinstance(v, (dict, list)):
                    results.extend(find_story_with_share(v, f"{path}.{k}"))
        elif isinstance(d, list):
            for idx, item in enumerate(d):
                if isinstance(item, (dict, list)):
                    results.extend(find_story_with_share(item, f"{path}[{idx}]"))
        return results
    
    nodes = find_story_with_share(data)
    print(f"  Found {len(nodes)} relevant nodes")
    
    # Also search for the immediate parent of share_url containing our token
    def find_share_url_context(d, path=""):
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, str) and share_token in v:
                    print(f"  Key '{k}' at {path} contains share token: {v[:200]}")
                elif isinstance(v, (dict, list)):
                    find_share_url_context(v, f"{path}.{k}")
        elif isinstance(d, list):
            for idx, item in enumerate(d):
                if isinstance(item, str) and share_token in item:
                    print(f"  List item at {path}[{idx}] contains share token: {item[:200]}")
                elif isinstance(item, (dict, list)):
                    find_share_url_context(item, f"{path}[{idx}]")
    
    print("\n--- Share token locations ---")
    find_share_url_context(data)
    break

# Also check: how many playable_url entries are there total across ALL scripts?
total_playable = 0
unique_playable = set()
for s in scripts:
    for m in re.finditer(r'"playable_url"\s*:\s*"([^"]+)"', s):
        pu = m.group(1).replace("\\/", "/")
        if "fbcdn.net" in pu:
            unique_playable.add(pu[:80])
            total_playable += 1

print(f"\n\nTotal playable_url entries across all scripts: {total_playable}")
print(f"Unique playable_url (by first 80 chars): {len(unique_playable)}")

# Count scripts with playable_url
scripts_with_playable = 0
for s in scripts:
    if '"playable_url"' in s:
        scripts_with_playable += 1
print(f"Scripts containing playable_url: {scripts_with_playable}")
