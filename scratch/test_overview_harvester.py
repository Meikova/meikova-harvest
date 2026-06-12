import sys
import os
import json
import re
from urllib.parse import urlparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_harvest(url):
    print(f"\n================ Testing URL: {url} ================")
    import requests as req
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = req.get(url, headers=headers, verify=False, timeout=12)
    html = resp.text
    clean_html = html.replace('\\/', '/').replace('\\', '')
    
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    path_segments = [seg for seg in parsed_url.path.split('/') if seg]
    last_segment = path_segments[-1] if path_segments else ""
    
    # 1. Try to extract current movie's ID
    main_movie_id = ""
    movie_match = re.search(r'"movie"\s*:\s*\{\s*"id"\s*:\s*"(\d+)"', clean_html)
    if movie_match:
        main_movie_id = movie_match.group(1)
    if not main_movie_id:
        movie_match = re.search(r'"movieId"\s*:\s*"([a-zA-Z0-9_-]+)"', clean_html)
        if movie_match:
            main_movie_id = movie_match.group(1)
    if not main_movie_id:
        # Check if there is postId (WordPress style)
        movie_match = re.search(r'"postId"\s*:\s*(\d+)', clean_html)
        if movie_match:
            main_movie_id = movie_match.group(1)
            
    print(f"Parsed Main Movie ID: {main_movie_id}")
    
    # Parse episodes
    episode_pattern = r'\{[^{}]*"server"[^{}]*"name"[^{}]*"slug"[^{}]*"link"[^{}]*\}'
    ep_matches = re.findall(episode_pattern, clean_html)
        
    print(f"Total episode matches parsed: {len(ep_matches)}")
    
    video_options = []
    all_parsed_options = []
    seen_urls = set()
    
    def get_digits(text):
        digits = "".join(re.findall(r'\d+', text))
        return int(digits) if digits else None
        
    last_val = get_digits(last_segment)
    
    for ep_str in ep_matches:
        try:
            if not ep_str.startswith('{'): ep_str = '{' + ep_str
            if not ep_str.endswith('}'): ep_str = ep_str + '}'
            
            # Filter by movie_id if we have one
            movie_id_match = re.search(r'"movie_id"\s*:\s*"([^"]+)"', ep_str)
            if movie_id_match and main_movie_id:
                if movie_id_match.group(1) != main_movie_id:
                    continue
                    
            server = re.search(r'"server"\s*:\s*"([^"]+)"', ep_str)
            name = re.search(r'"name"\s*:\s*"([^"]+)"', ep_str)
            slug = re.search(r'"slug"\s*:\s*"([^"]+)"', ep_str)
            link = re.search(r'"link"\s*:\s*"([^"]+)"', ep_str)
            type_match = re.search(r'"type"\s*:\s*"([^"]+)"', ep_str)
            
            if link:
                media_url = link.group(1)
                if media_url.startswith('/'):
                    if 'fcloud.live' in clean_html:
                        media_url = 'https://fcloud.live' + media_url
                    else:
                        media_url = f"https://{domain}" + media_url

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
                if is_stream:
                    type_val = type_match.group(1) if type_match else ""
                    type_suffix = f" [{type_val.upper()}]" if type_val else ""
                    option_obj = {
                        "format_id": "",
                        "resolution": "Auto Stream",
                        "ext": "mp4",
                        "type": "video",
                        "size": "Unknown Size",
                        "label": f"Server: {server_val}{type_suffix} (Episode {name_val})",
                        "url": media_url
                    }
                    if is_match:
                        seen_urls.add(media_url)
                        option_obj["format_id"] = f"direct_video_{len(video_options)+1}"
                        video_options.append(option_obj)
                    else:
                        all_parsed_options.append(option_obj)
        except Exception as e:
            print("Error parsing match:", e)
            
    if not video_options and all_parsed_options:
        for opt in all_parsed_options:
            if opt["url"] not in seen_urls:
                seen_urls.add(opt["url"])
                opt["format_id"] = f"direct_video_{len(video_options)+1}"
                video_options.append(opt)
                
    print(f"Final options returned count: {len(video_options)}")
    if video_options:
        print("First 3 options (encoded to ascii safe):")
        for opt in video_options[:3]:
            label_safe = opt['label'].encode('ascii', 'replace').decode('ascii')
            print(f"- {label_safe}: {opt['url']}")
        print("Last 3 options (encoded to ascii safe):")
        for opt in video_options[-3:]:
            label_safe = opt['label'].encode('ascii', 'replace').decode('ascii')
            print(f"- {label_safe}: {opt['url']}")

test_harvest("https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256/tap-1")
test_harvest("https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256")
