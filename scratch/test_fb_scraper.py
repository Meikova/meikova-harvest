import requests
import json
import re
import urllib.parse

def scrape_fb_post(url, client_id=None):
    session = requests.Session()
    headers = {
        "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_patched.html)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    try:
        res = session.get(url, headers=headers, timeout=15)
        html = res.text
        status_code = res.status_code
        final_url = res.url
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch Facebook page: {e}"}
        
    if status_code != 200:
        return {"status": "error", "message": f"Facebook returned status code {status_code}"}
        
    # Extract Title and Description from Meta tags
    title = ""
    desc_match = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', html) or re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html)
    if desc_match:
        title = desc_match.group(1)
        # Unescape HTML entities
        import html as html_lib
        title = html_lib.unescape(title)
        
    title_match = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html)
    uploader = "Facebook User"
    if title_match:
        full_title = html_lib.unescape(title_match.group(1))
        # og:title is usually "Uploader Name" or "Uploader Name - Post Title"
        if " - " in full_title:
            uploader = full_title.split(" - ")[0]
        else:
            uploader = full_title
            
    if not title:
        title = f"Facebook Post by {uploader}"
        
    # Extract Thumbnail
    thumbnail = ""
    thumb_match = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
    if thumb_match:
        thumbnail = html_lib.unescape(thumb_match.group(1))
        
    # Find all application/json script blocks
    scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
    
    video_options = []
    images = []
    
    # Recursive search function for GraphQL data
    def search_graphql(d):
        if isinstance(d, dict):
            # Check for photos in subattachments
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
                                    if uri not in images:
                                        images.append(uri)
            
            # Check for direct Photo types
            if d.get("__typename") == "Photo" or "viewer_image" in d:
                v_img = d.get("viewer_image")
                if isinstance(v_img, dict) and v_img.get("uri"):
                    uri = v_img["uri"].replace("\\/", "/").replace("\\u0025", "%")
                    uri = urllib.parse.unquote(uri)
                    if uri not in images:
                        images.append(uri)
                else:
                    img = d.get("image")
                    if isinstance(img, dict) and img.get("uri"):
                        uri = img["uri"].replace("\\/", "/").replace("\\u0025", "%")
                        uri = urllib.parse.unquote(uri)
                        if uri not in images:
                            images.append(uri)
                            
            # Check for Video options (playable_url or progressive_url)
            if "playable_url" in d or "progressive_url" in d:
                playable = d.get("playable_url") or d.get("progressive_url")
                if playable and isinstance(playable, str) and "fbcdn.net" in playable:
                    playable = playable.replace("\\/", "/").replace("\\u0025", "%")
                    playable = urllib.parse.unquote(playable)
                    
                    # Avoid dash/low quality chunks
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
                        if playable not in [o["url"] for o in video_options]:
                            video_options.append(opt)
                            
            for v in d.values():
                if isinstance(v, (dict, list)):
                    search_graphql(v)
        elif isinstance(d, list):
            for item in d:
                if isinstance(item, (dict, list)):
                    search_graphql(item)

    for script_text in scripts:
        try:
            data = json.loads(script_text)
            search_graphql(data)
        except:
            pass

    # If we found no photos but found og:image, add it
    if not images and thumbnail:
        images.append(thumbnail)
        
    # Map photos to video_options if no video exists
    if not video_options and images:
        for idx, img_url in enumerate(images):
            video_options.append({
                "format_id": f"direct_photo_{idx+1}",
                "ext": "jpg",
                "resolution": "Original",
                "size": "Unknown Size",
                "label": f"Photo Option {idx+1}",
                "url": img_url
            })

    return {
        "status": "success",
        "title": title,
        "duration": "0:05" if not video_options or any("photo" in o["format_id"] for o in video_options) else "0:30",
        "uploader": uploader,
        "thumbnail": thumbnail or (images[0] if images else ""),
        "views": "N/A",
        "likes": "N/A",
        "upload_date": "Recent",
        "category": "Facebook Post",
        "tags": ["Post"],
        "subtitles": [],
        "video_options": video_options,
        "audio_options": [],
        "images": images,
        "platform": "Facebook",
        "platform_class": "facebook"
    }

url = "https://www.facebook.com/share/p/18KCdDUac7/"
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
print("Testing facebook post scraping...")
res = scrape_fb_post(url)
print(json.dumps(res, indent=2, ensure_ascii=False))
