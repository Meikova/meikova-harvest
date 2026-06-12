import requests as req
import re
import urllib3
from urllib.parse import urlparse, parse_qs, urljoin
urllib3.disable_warnings()

url = "https://motchilltv.lt/episodes/bai-hoc-dang-doi-tap-1/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print("Fetching main page...")
resp = req.get(url, headers=headers, verify=False, timeout=12)
print(f"Main page status: {resp.status_code}")
html = resp.text

parsed_url = urlparse(url)
domain = parsed_url.netloc
path_segments = [seg for seg in parsed_url.path.split('/') if seg]

video_options = []
seen_urls = set()

# Find all dooplay player option elements
li_tags = re.findall(r'<li[^>]+class=["\'][^"\']*dooplay_player_option[^"\']*["\'][^>]*>.*?</li>', html, re.IGNORECASE | re.DOTALL)
print(f"Found {len(li_tags)} dooplay player option elements.")

# Determine base AJAX url
ajax_url = f"{parsed_url.scheme}://{domain}/wp-admin/admin-ajax.php"

# Determine episode name
ep_name = "1"
title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
title_val = title_match.group(1).strip() if title_match else ""
ep_match = re.search(r'(?:Tập|Tap|Episode|Ep)\s*(\d+)', title_val, re.IGNORECASE)
if ep_match:
    ep_name = ep_match.group(1)
else:
    last_seg = path_segments[-1] if path_segments else ""
    url_ep_match = re.search(r'(?:tap|episode|ep)[-_]?(\d+)', last_seg, re.IGNORECASE)
    if url_ep_match:
        ep_name = url_ep_match.group(1)
    else:
        digit_match = re.search(r'-(\d+)$', last_seg)
        if digit_match:
            ep_name = digit_match.group(1)

print(f"Determined episode name: {ep_name}")

# Make AJAX calls
for tag in li_tags:
    try:
        post_m = re.search(r'data-post=["\'](\d+)["\']', tag)
        nume_m = re.search(r'data-nume=["\'](\d+)["\']', tag)
        type_m = re.search(r'data-type=["\']([^"\']+)["\']', tag)
        
        if post_m and nume_m:
            post_id = post_m.group(1)
            nume = nume_m.group(1)
            dtype = type_m.group(1) if type_m else "tv"
            
            # Extract title and server
            title_m = re.search(r'<span class=["\']title["\']>(.*?)</span>', tag, re.IGNORECASE)
            server_m = re.search(r'<span class=["\']server["\']>(.*?)</span>', tag, re.IGNORECASE)
            
            t_val = title_m.group(1).strip() if title_m else f"Option {nume}"
            s_val = server_m.group(1).strip() if server_m else "DooPlay"
            
            print(f"\nProcessing option {nume}: {t_val} ({s_val})")
            
            # Call AJAX post
            ajax_headers = {
                "User-Agent": headers["User-Agent"],
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": url
            }
            ajax_data = {
                "action": "doo_player_ajax",
                "post": post_id,
                "nume": nume,
                "type": dtype
            }
            
            ajax_resp = req.post(ajax_url, headers=ajax_headers, data=ajax_data, verify=False, timeout=8)
            if ajax_resp.status_code == 200:
                res_json = ajax_resp.json()
                embed_url = res_json.get("embed_url")
                print(f"Embed URL: {embed_url}")
                if embed_url:
                    stream_url = embed_url
                    resolved = False
                    
                    # Check if it has a direct stream url in query parameters
                    parsed_embed = urlparse(embed_url)
                    queries = parse_qs(parsed_embed.query)
                    for val_list in queries.values():
                        for val in val_list:
                            if val.startswith("http") and (".m3u8" in val or ".mp4" in val):
                                stream_url = val
                                resolved = True
                                print(f"Resolved from query: {stream_url}")
                                break
                        if resolved:
                            break
                    
                    # Otherwise, fetch page and extract
                    if not resolved:
                        print(f"Fetching embed page: {embed_url}")
                        embed_resp = req.get(embed_url, headers={"User-Agent": headers["User-Agent"], "Referer": url}, verify=False, timeout=8)
                        if embed_resp.status_code == 200:
                            embed_html = embed_resp.text
                            url_match = re.search(r'const\s+url\s*=\s*["\']([^"\']+)["\']', embed_html)
                            if url_match:
                                stream_url = urljoin(embed_url, url_match.group(1))
                                resolved = True
                                print(f"Resolved from 'const url': {stream_url}")
                            else:
                                src_match = re.search(r'(?:file|source|url)\s*:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', embed_html, re.IGNORECASE)
                                if src_match:
                                    stream_url = urljoin(embed_url, src_match.group(1))
                                    resolved = True
                                    print(f"Resolved from source/file pattern: {stream_url}")
                                else:
                                    m3u8_matches = re.findall(r'https?://[^\s"\'\\<>#]+\.(?:m3u8|mp4)[^\s"\'\\<>#]*', embed_html)
                                    if m3u8_matches:
                                        stream_url = m3u8_matches[0]
                                        resolved = True
                                        print(f"Resolved from raw regex matches: {stream_url}")
                    
                    type_suffix = " [M3U8]" if (".m3u8" in stream_url) else " [EMBED]"
                    label_name = f"Server: {t_val}{type_suffix}"
                    if ep_name:
                        label_name += f" (Episode {ep_name})"
                        
                    if stream_url not in seen_urls:
                        seen_urls.add(stream_url)
                        video_options.append({
                            "format_id": f"direct_video_{len(video_options)+1}",
                            "resolution": "Auto Stream",
                            "ext": "mp4",
                            "type": "video",
                            "size": "Unknown Size",
                            "label": label_name,
                            "episode": ep_name,
                            "server": f"Server: {t_val}{type_suffix}",
                            "url": stream_url
                        })
    except Exception as ex:
        print(f"Failed to process DooPlay option: {ex}")

print("\n--- FINAL VIDEO OPTIONS ---")
for opt in video_options:
    print(opt)
