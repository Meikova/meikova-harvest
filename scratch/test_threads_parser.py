import requests
import json
import re
import sys
import os
import http.cookiejar

# Set stdout/stderr to UTF-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def extract_shortcode(url):
    # Match shortcode from threads URL
    # https://www.threads.net/@chipmunk.8255885/post/DZWqikzmsye?xmt=...
    # or https://threads.net/t/DZWqikzmsye
    match = re.search(r'/post/([^/?#]+)', url)
    if not match:
        match = re.search(r'/t/([^/?#]+)', url)
    return match.group(1) if match else None

def load_cookies_into_session(cookie_file, session):
    cookie_jar = http.cookiejar.MozillaCookieJar()
    try:
        cookie_jar.load(cookie_file, ignore_discard=True, ignore_expires=True)
        session.cookies.update(cookie_jar)
        
        # Replicate to Threads domains
        replicated_count = 0
        for cookie in list(session.cookies):
            domain = getattr(cookie, 'domain', '')
            if 'instagram.com' in domain or 'instagr.am' in domain or 'facebook.com' in domain:
                for target_domain in ['.threads.net', '.threads.com', 'www.threads.net', 'threads.net', 'threads.com', 'www.threads.com']:
                    new_cookie = requests.cookies.create_cookie(
                        name=cookie.name,
                        value=cookie.value,
                        domain=target_domain,
                        path=cookie.path,
                        secure=cookie.secure,
                        expires=cookie.expires
                    )
                    session.cookies.set_cookie(new_cookie)
                    replicated_count += 1
        print(f"Loaded {len(session.cookies)} cookies and replicated {replicated_count} to Threads domains.")
    except Exception as e:
        print(f"Error loading cookies: {e}")

def parse_threads_page(url, client_id=None):
    shortcode = extract_shortcode(url)
    if not shortcode:
        return {"status": "error", "message": "Không thể trích xuất shortcode từ URL Threads."}
        
    print(f"Shortcode extracted: {shortcode}")
    
    session = requests.Session()
    
    # Try fetching anonymously first
    headers = {
        "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_patched.html)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    print("Attempting anonymous fetch...")
    res = session.get(url, headers=headers, timeout=15)
    print("Fetch status:", res.status_code)
    
    # If anonymous fetch fails or redirects to login, attempt with cookies
    html = res.text
    if res.status_code != 200 or "login" in res.url.lower():
        print("Anonymous fetch redirected or failed. Retrying with cookies...")
        session = requests.Session() # reset session
        # Check client cookies
        cookies_dir = "downloads/cookies"
        cookie_files = [f for f in os.listdir(cookies_dir) if f.startswith("cookies_") and f.endswith(".txt")]
        if cookie_files:
            cookie_file = os.path.join(cookies_dir, cookie_files[0])
            load_cookies_into_session(cookie_file, session)
            
            res = session.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            }, timeout=15)
            print("Fetch status with cookies:", res.status_code)
            html = res.text
        else:
            print("No cookies available to retry.")
            
    # Extract scripts
    scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
    print(f"Total script tags parsed: {len(scripts)}")
    
    def search_key(d, target_key, found_list):
        if isinstance(d, dict):
            for k, v in d.items():
                if k == target_key:
                    found_list.append(v)
                if isinstance(v, (dict, list)):
                    search_key(v, target_key, found_list)
        elif isinstance(d, list):
            for item in d:
                search_key(item, target_key, found_list)

    # Search for thread_items in scripts
    all_thread_items = []
    for script_text in scripts:
        try:
            data = json.loads(script_text)
            temp = []
            search_key(data, "thread_items", temp)
            for items_list in temp:
                if isinstance(items_list, list):
                    all_thread_items.extend(items_list)
        except:
            pass
            
    # Look for the target post matching the shortcode
    target_post = None
    for item in all_thread_items:
        post = item.get("post")
        if post and post.get("code") == shortcode:
            target_post = post
            break
            
    if not target_post:
        # Fallback search: look for any post where code matches (even if not under thread_items)
        for script_text in scripts:
            try:
                data = json.loads(script_text)
                temp = []
                search_key(data, "post", temp)
                for post in temp:
                    if isinstance(post, dict) and post.get("code") == shortcode:
                        target_post = post
                        break
                if target_post:
                    break
            except:
                pass
                
    if not target_post:
        return {"status": "error", "message": "Không tìm thấy dữ liệu bài viết Threads tương ứng với shortcode này."}
        
    # Extract info from target_post
    uploader = target_post.get("user", {}).get("username", "Threads User")
    uploader_pic = target_post.get("user", {}).get("profile_pic_url", "")
    caption_text = target_post.get("caption", {}).get("text", "")
    likes = target_post.get("like_count", 0)
    replies = target_post.get("text_post_app_info", {}).get("direct_reply_count", 0)
    taken_at = target_post.get("taken_at")
    
    media_type = target_post.get("media_type") # 1: Image, 2: Video, 8: Carousel
    
    video_options = []
    images = []
    
    # Process images helper
    def extract_image_url(image_versions2):
        if not image_versions2:
            return None
        candidates = image_versions2.get("candidates", [])
        if candidates:
            # Sort by width descending
            candidates = sorted(candidates, key=lambda x: x.get("width", 0), reverse=True)
            return candidates[0].get("url")
        return None

    if media_type == 8: # Carousel
        carousel_media = target_post.get("carousel_media", []) or []
        for idx, item in enumerate(carousel_media):
            item_type = item.get("media_type")
            img_url = extract_image_url(item.get("image_versions2"))
            if img_url:
                images.append({
                    "label": f"Slide Photo {idx+1}",
                    "url": img_url,
                    "ext": "jpg"
                })
            
            # If video slide
            video_versions = item.get("video_versions", [])
            if video_versions:
                video_versions = sorted(video_versions, key=lambda x: x.get("width", 0), reverse=True)
                v_url = video_versions[0].get("url")
                video_options.append({
                    "format_id": f"slide_video_{idx+1}",
                    "ext": "mp4",
                    "resolution": f"Slide {idx+1}",
                    "size": "Unknown Size",
                    "label": f"Video Slide {idx+1}",
                    "url": v_url
                })
    elif media_type == 2 or target_post.get("video_versions"): # Video
        video_versions = target_post.get("video_versions", [])
        if video_versions:
            video_versions = sorted(video_versions, key=lambda x: x.get("width", 0), reverse=True)
            v_url = video_versions[0].get("url")
            video_options.append({
                "format_id": "direct_video",
                "ext": "mp4",
                "resolution": "Original",
                "size": "Unknown Size",
                "label": "Video",
                "url": v_url
            })
        
        # Thumbnail for video
        img_url = extract_image_url(target_post.get("image_versions2"))
        if img_url:
            images.append({
                "label": "Video Thumbnail",
                "url": img_url,
                "ext": "jpg"
            })
    else: # Image / fallback
        img_url = extract_image_url(target_post.get("image_versions2"))
        if img_url:
            images.append({
                "label": "Photo",
                "url": img_url,
                "ext": "jpg"
            })
            
    # If it is text only
    if not images and not video_options:
        return {
            "status": "error",
            "message": "Bài viết Threads này chỉ chứa văn bản và không có hình ảnh hoặc video để tải xuống."
        }
        
    thumbnail = images[0]["url"] if images else ""
    
    result = {
        "status": "success",
        "title": caption_text[:80] + "..." if len(caption_text) > 80 else (caption_text or "Threads Post"),
        "duration": "0:05", # default
        "uploader": uploader,
        "uploader_pic": uploader_pic,
        "thumbnail": thumbnail,
        "views": "N/A",
        "likes": f"{likes:,}" if likes else "0",
        "upload_date": "Đang tải...", # Will convert timestamp if needed
        "category": "Threads Post",
        "tags": ["Threads"],
        "subtitles": [],
        "video_options": video_options,
        "audio_options": [], # Will fill inside info route
        "images": images,
        "platform": "Threads",
        "platform_class": "threads",
        "platform_label": "Threads"
    }
    return result

# Run test
url = "https://www.threads.net/@chipmunk.8255885/post/DZWqikzmsye"
res_data = parse_threads_page(url)
print("\n--- Parsed Results ---")
print(json.dumps(res_data, indent=2, ensure_ascii=False))
