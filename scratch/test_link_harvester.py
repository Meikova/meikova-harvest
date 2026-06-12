import requests
import re
import urllib3
import json
from urllib.parse import urlparse
urllib3.disable_warnings()

def harvest_links_from_html(page_url, html):
    # Parse page URL info
    parsed_url = urlparse(page_url)
    domain = parsed_url.netloc
    
    # Get page path segments
    path_segments = [seg for seg in parsed_url.path.split('/') if seg]
    last_segment = path_segments[-1] if path_segments else ""
    
    # Extract Title
    title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else "Unknown Video"
    
    # Extract Thumbnail
    thumb_match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE) or \
                  re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html, re.IGNORECASE)
    thumbnail = thumb_match.group(1).strip() if thumb_match else ""
    
    # Clean up backslashes commonly found in JSON data on pages
    clean_html = html.replace('\\/', '/').replace('\\', '')
    
    # Let's find all episodes / links via JSON structures
    episode_pattern = r'\{[^{}]*"server"[^{}]*"name"[^{}]*"slug"[^{}]*"link"[^{}]*\}'
    ep_matches = re.findall(episode_pattern, clean_html)
    
    video_options = []
    seen_urls = set()
    
    print(f"Discovered {len(ep_matches)} episode-like JSON objects in HTML.")
    
    # Helper to get numeric value
    def get_digits(text):
        digits = "".join(re.findall(r'\d+', text))
        return int(digits) if digits else None
        
    last_val = get_digits(last_segment)
    
    # 1. Match against episode list objects
    for ep_str in ep_matches:
        try:
            if not ep_str.startswith('{'): ep_str = '{' + ep_str
            if not ep_str.endswith('}'): ep_str = ep_str + '}'
            
            server = re.search(r'"server"\s*:\s*"([^"]+)"', ep_str)
            name = re.search(r'"name"\s*:\s*"([^"]+)"', ep_str)
            slug = re.search(r'"slug"\s*:\s*"([^"]+)"', ep_str)
            link = re.search(r'"link"\s*:\s*"([^"]+)"', ep_str)
            type_val = re.search(r'"type"\s*:\s*"([^"]+)"', ep_str)
            
            if link:
                media_url = link.group(1)
                if media_url.startswith('/'):
                    if 'fcloud.live' in clean_html:
                        media_url = 'https://fcloud.live' + media_url
                    else:
                        media_url = f"https://{domain}" + media_url

                if media_url in seen_urls:
                    continue
                
                slug_val = slug.group(1) if slug else ""
                name_val = name.group(1) if name else ""
                server_val = server.group(1) if server else "Server"
                
                is_match = False
                if last_segment:
                    if last_segment.lower() == slug_val.lower():
                        is_match = True
                    else:
                        name_val_digits = get_digits(name_val)
                        slug_val_digits = get_digits(slug_val)
                        if last_val is not None:
                            if last_val == name_val_digits or last_val == slug_val_digits:
                                    is_match = True
                                    
                is_stream = (media_url.endswith('.m3u8') or '.m3u8' in media_url or 
                             media_url.endswith('.mp4') or '/player/master/' in media_url)
                if is_match and is_stream:
                    seen_urls.add(media_url)
                    video_options.append({
                        "format_id": f"direct_video_{len(video_options)+1}",
                        "resolution": "Auto Stream",
                        "ext": "mp4",
                        "type": "video",
                        "size": "Unknown Size",
                        "label": f"Server: {server_val} (Episode {name_val})",
                        "url": media_url
                    })
        except Exception as json_err:
            pass
            
    # 2. Fallback: If no matched episodes found, search page for any raw .m3u8 or .mp4 links
    if not video_options:
        raw_m3u8_links = re.findall(r'https?://[^\s"\'\\<>#]+\.(?:m3u8|mp4)[^\s"\'\\<>#]*', clean_html)
        for link in raw_m3u8_links:
            link = link.rstrip('\\').rstrip('"').rstrip("'")
            if link not in seen_urls:
                seen_urls.add(link)
                video_options.append({
                    "format_id": f"direct_video_{len(video_options)+1}",
                    "resolution": "Auto Stream",
                    "ext": "mp4",
                    "type": "video",
                    "size": "Unknown Size",
                    "label": f"Direct Link #{len(video_options)+1}",
                    "url": link
                })
                
    return {
        "status": "success",
        "title": title,
        "uploader": domain,
        "thumbnail": thumbnail,
        "video_options": video_options,
        "audio_options": [],
        "subtitles": {},
        "images": [{"label": "Thumbnail", "url": thumbnail, "ext": "jpg"}] if thumbnail else []
    }

if __name__ == "__main__":
    url = "https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256/tap-1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    resp = requests.get(url, headers=headers, verify=False, timeout=15)
    result = harvest_links_from_html(url, resp.text)
    
    print("\nHarvesting completed successfully.")
    with open("scratch/harvester_output.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("Output written to scratch/harvester_output.json")
