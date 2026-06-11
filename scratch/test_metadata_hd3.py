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

post_id = "2063872181207156"
scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)

# Check how many scripts contain our post_id
found_scripts = []
for i, s in enumerate(scripts):
    if post_id in s:
        found_scripts.append(i)
print(f"Scripts containing post_id '{post_id}': {found_scripts}")

# Check what format post_id appears in
for i in found_scripts[:3]:
    s = scripts[i]
    idx = s.find(post_id)
    context = s[max(0,idx-50):idx+len(post_id)+50]
    print(f"\nScript {i} context: ...{context}...")

# Try to find the post node
for i in found_scripts:
    s = scripts[i]
    try:
        data = json.loads(s)
    except:
        continue
    
    def find_post(d, depth=0):
        if depth > 30:
            return None
        if isinstance(d, dict):
            if str(d.get("post_id")) == post_id or str(d.get("id")) == post_id:
                return d
            for v in d.values():
                if isinstance(v, (dict, list)):
                    r = find_post(v, depth+1)
                    if r: return r
        elif isinstance(d, list):
            for item in d:
                if isinstance(item, (dict, list)):
                    r = find_post(item, depth+1)
                    if r: return r
        return None
    
    post = find_post(data)
    if post:
        print(f"\nFOUND post node in script {i}!")
        print(f"  Keys: {list(post.keys())[:15]}")
        
        # Get actors
        actors = post.get("actors", [])
        for a in actors:
            if isinstance(a, dict):
                print(f"  Actor: {a.get('name')}")
        
        # Get message
        msg = post.get("message")
        if isinstance(msg, dict):
            print(f"  Message: {str(msg.get('text', ''))[:200]}")
        
        # Find Video nodes
        def find_videos(d, depth=0):
            vids = []
            if depth > 20: return vids
            if isinstance(d, dict):
                if d.get("__typename") == "Video":
                    vids.append(d)
                    return vids  # Don't recurse
                for v in d.values():
                    if isinstance(v, (dict, list)):
                        vids.extend(find_videos(v, depth+1))
            elif isinstance(d, list):
                for item in d:
                    if isinstance(item, (dict, list)):
                        vids.extend(find_videos(item, depth+1))
            return vids
        
        videos = find_videos(post)
        print(f"\n  Video nodes found: {len(videos)}")
        for vi, v in enumerate(videos):
            print(f"\n  Video {vi+1}:")
            print(f"    id: {v.get('id')}")
            for key in ["playable_url", "playable_url_quality_hd", "progressive_url", "width", "height"]:
                val = v.get(key)
                if val is None:
                    print(f"    {key}: None")
                elif isinstance(val, str) and len(val) > 80:
                    print(f"    {key}: {val[:80]}...")
                else:
                    print(f"    {key}: {val}")
        
        # Find progressive_url anywhere in post (not just Video nodes)
        prog_urls = set()
        def find_prog(d, depth=0):
            if depth > 25: return
            if isinstance(d, dict):
                pu = d.get("progressive_url")
                if pu and isinstance(pu, str) and "fbcdn" in pu:
                    prog_urls.add(pu.replace("\\/", "/")[:80])
                for v in d.values():
                    if isinstance(v, (dict, list)):
                        find_prog(v, depth+1)
            elif isinstance(d, list):
                for item in d:
                    if isinstance(item, (dict, list)):
                        find_prog(item, depth+1)
        find_prog(post)
        print(f"\n  All unique progressive_url in post: {len(prog_urls)}")
        for pu in prog_urls:
            print(f"    {pu}...")
        
        break
    else:
        print(f"\nScript {i}: post node NOT found")
