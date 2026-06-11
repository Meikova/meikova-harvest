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

# 1. Check og metadata
print("=== OG METADATA ===")
og_title = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html)
og_desc = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', html)
print(f"og:title: {og_title.group(1) if og_title else 'NOT FOUND'}")
print(f"og:desc: {og_desc.group(1)[:150] if og_desc else 'NOT FOUND'}")

# 2. Find post node and check video fields
post_id = "2063872181207156"
scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)

for i, s in enumerate(scripts):
    if f'"post_id":"{post_id}"' not in s:
        continue
    data = json.loads(s)
    
    def find_post(d):
        if isinstance(d, dict):
            if d.get("post_id") == post_id:
                return d
            for v in d.values():
                if isinstance(v, (dict, list)):
                    r = find_post(v)
                    if r: return r
        elif isinstance(d, list):
            for item in d:
                if isinstance(item, (dict, list)):
                    r = find_post(item)
                    if r: return r
        return None
    
    post = find_post(data)
    if not post:
        continue
    
    print(f"\n=== POST NODE (script {i}) ===")
    
    # Find actors (uploader name)
    actors = post.get("actors", [])
    if actors:
        for a in actors:
            if isinstance(a, dict):
                print(f"Actor: {a.get('name', 'N/A')}")
    
    # Find "to" field (group/page)
    to = post.get("to")
    if isinstance(to, dict):
        print(f"To: {to.get('name', 'N/A')}")
    
    # Find message text
    msg = post.get("message")
    if isinstance(msg, dict) and "text" in msg:
        print(f"Message: {str(msg['text'])[:200]}")
    
    # Find ALL Video nodes and their fields
    print(f"\n=== VIDEO NODES ===")
    video_count = [0]
    def find_videos(d, path=""):
        if isinstance(d, dict):
            if d.get("__typename") == "Video":
                video_count[0] += 1
                print(f"\nVideo #{video_count[0]} at {path}:")
                print(f"  id: {d.get('id', 'N/A')}")
                for key in sorted(d.keys()):
                    val = d[key]
                    if key in ["playable_url", "playable_url_quality_hd", "progressive_url",
                               "browser_native_hd_url", "browser_native_sd_url",
                               "width", "height", "original_width", "original_height", 
                               "is_live_streaming", "name", "title", "__typename"]:
                        if isinstance(val, str) and len(val) > 120:
                            val = val[:120] + "..."
                        print(f"  {key}: {val}")
                # Check for all progressive/playable URLs even if empty
                for key in ["playable_url", "playable_url_quality_hd", "progressive_url"]:
                    if key not in d:
                        print(f"  {key}: [KEY MISSING]")
                return  # Don't recurse into video nodes to avoid duplicates
            
            for k, v in d.items():
                if isinstance(v, (dict, list)):
                    find_videos(v, f"{path}.{k}")
        elif isinstance(d, list):
            for idx, item in enumerate(d):
                if isinstance(item, (dict, list)):
                    find_videos(item, f"{path}[{idx}]")
    
    find_videos(post)
    
    # Also find progressive_url that's NOT inside a Video node
    print(f"\n=== ALL progressive_url IN POST ===")
    prog_urls = []
    def find_prog(d):
        if isinstance(d, dict):
            if "progressive_url" in d and d["progressive_url"]:
                pu = d["progressive_url"]
                if isinstance(pu, str):
                    prog_urls.append(pu)
            for v in d.values():
                if isinstance(v, (dict, list)):
                    find_prog(v)
        elif isinstance(d, list):
            for item in d:
                if isinstance(item, (dict, list)):
                    find_prog(item)
    find_prog(post)
    unique_prog = set()
    for pu in prog_urls:
        decoded = pu.replace("\\/", "/")
        short = decoded[:80]
        if short not in unique_prog:
            unique_prog.add(short)
            print(f"  {decoded[:150]}...")
    print(f"Total unique progressive_url: {len(unique_prog)}")
    
    break
