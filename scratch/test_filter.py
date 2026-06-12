import sys
import os
import requests
import re
import urllib3
urllib3.disable_warnings()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# We run the test without importing app

url = "https://phimchillhd.net/phim/giao-duc-chan-chinh/tap-10_1353095.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://phimchillhd.net/"
}

resp = requests.get(url, headers=headers, verify=False, timeout=25)
page_html = resp.text

# Now we run the extraction logic manually but print the options at each stage
import urllib.parse
from urllib.parse import urlparse, urljoin, parse_qs

page_url = url
page_domain = "phimchillhd.net"
parsed_url = urlparse(url)
page_path_segments = [s for s in parsed_url.path.split('/') if s]
page_last_segment = page_path_segments[-1] if page_path_segments else ""

# Let's run the exact extract_single_page_options logic
opts = []
seen = set()

# Determine episode name dynamically
ep_name = "9"

# 5. Check data-link elements
data_link_elements = re.findall(r'<a[^>]+data-link=["\']([^"\']+)["\'][^>]*>(.*?)</a>', page_html, re.IGNORECASE | re.DOTALL)
print(f"Total data-link elements found: {len(data_link_elements)}")

for embed_url, inner_text in data_link_elements:
    t_val = re.sub(r'<[^>]+>', '', inner_text).strip()
    t_val = t_val if t_val else "Server"
    
    stream_url = embed_url
    resolved = False
    
    parsed_embed = urlparse(embed_url)
    queries = parse_qs(parsed_embed.query)
    for val_list in queries.values():
        for val in val_list:
            if val.startswith("http") and (".m3u8" in val or ".mp4" in val):
                stream_url = val
                resolved = True
                break
        if resolved:
            break
            
    is_direct = (stream_url.endswith('.m3u8') or '.m3u8' in stream_url or 
                 stream_url.endswith('.mp4') or '.mp4' in stream_url)
                 
    if not resolved and not is_direct:
        # We simulate the requests.get to resolve it
        embed_resp = requests.get(embed_url, headers={"User-Agent": headers["User-Agent"], "Referer": page_url}, verify=False, timeout=10)
        if embed_resp.status_code == 200:
            embed_html = embed_resp.text
            obf_match = re.search(r'data-obf=["\']([^"\']+)["\']', embed_html)
            if obf_match:
                try:
                    import base64
                    import json
                    decoded_obf = json.loads(base64.b64decode(obf_match.group(1)).decode('utf-8'))
                    s_ub_val = decoded_obf.get("sUb")
                    if s_ub_val:
                        stream_url = urljoin(embed_url, f"/{s_ub_val}.m3u8")
                        resolved = True
                except Exception as e:
                    print("Error decoding obf:", e)
                    
    type_suffix = " [M3U8]" if (".m3u8" in stream_url) else " [EMBED]"
    label_name = f"Server: {t_val}{type_suffix}"
    if ep_name:
        label_name += f" (Episode {ep_name})"
        
    print(f"Processing option: label_name='{label_name}' | url='{stream_url}'")
    if stream_url not in seen:
        seen.add(stream_url)
        seen.add(embed_url)
        opts.append({
            "format_id": "",
            "resolution": "Auto Stream",
            "ext": "mp4",
            "type": "video",
            "size": "Unknown Size",
            "label": label_name,
            "episode": ep_name,
            "server": f"Server: {t_val}{type_suffix}",
            "url": stream_url
        })

print(f"\nBefore filtering, opts has {len(opts)} items:")
for opt in opts:
    print(f"  - server='{opt['server']}' | ep='{opt['episode']}' | url='{opt['url']}'")

# Apply the filtering
best_opts = {}
for opt in opts:
    server_key = opt["server"]
    ep_key = opt["episode"]
    key = (server_key, ep_key)
    
    if key not in best_opts:
        best_opts[key] = opt
    else:
        existing = best_opts[key]
        existing_has_size = (existing.get("size") != "Unknown Size")
        opt_has_size = (opt.get("size") != "Unknown Size")
        
        if opt_has_size and not existing_has_size:
            best_opts[key] = opt
        elif not opt_has_size and existing_has_size:
            pass
        else:
            existing_is_streamc = ("streamc.xyz" in existing.get("url", ""))
            opt_is_streamc = ("streamc.xyz" in opt.get("url", ""))
            if existing_is_streamc and not opt_is_streamc:
                best_opts[key] = opt

filtered_opts = list(best_opts.values())
print(f"\nAfter filtering, filtered_opts has {len(filtered_opts)} items:")
for opt in filtered_opts:
    print(f"  - server='{opt['server']}' | ep='{opt['episode']}' | url='{opt['url']}'")
