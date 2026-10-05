import os
import json
import re
import logging
import http.cookiejar
import requests
from concurrent.futures import ThreadPoolExecutor

from config import TEMP_DOWNLOAD_DIR
from utils.helpers import get_url_content_length, format_size, format_duration

logger = logging.getLogger(__name__)

def extract_shortcode(url):
    """Match shortcode from threads URL."""
    match = re.search(r'/post/([^/?#\s]+)', url)
    if not match:
        match = re.search(r'/t/([^/?#\s]+)', url)
    return match.group(1) if match else None


def parse_threads_page(url, client_id=None):
    shortcode = extract_shortcode(url)
    if not shortcode:
        return {"status": "error", "message": "Unable to extract shortcode from Threads URL."}
        
    session = requests.Session()
    
    # Try fetching anonymously first
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
        html = ""
        status_code = 500
        final_url = url
        logger.warning(f"Anonymous Threads fetch failed: {e}")
    
    # If anonymous fetch fails, redirects to login, or status is not 200, attempt with cookies
    if status_code != 200 or "login" in final_url.lower() or "Confirm you're not a bot".lower() in html.lower():
        session = requests.Session() # reset session
        from utils.cookies import get_cookie_file_path
        cookie_file = get_cookie_file_path(client_id) if client_id else None
        
        if cookie_file and os.path.exists(cookie_file):
            cookie_jar = http.cookiejar.MozillaCookieJar()
            try:
                cookie_jar.load(cookie_file, ignore_discard=True, ignore_expires=True)
                session.cookies.update(cookie_jar)
                
                # Replicate to Threads domains
                for cookie in list(session.cookies):
                    domain = getattr(cookie, 'domain', '')
                    if any(x in domain for x in ['instagram.com', 'instagr.am', 'facebook.com']):
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
            except Exception as e:
                logger.warning(f"Error loading cookies for Threads: {e}")
                
            try:
                res = session.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                }, timeout=15)
                html = res.text
            except Exception as e:
                html = ""
                logger.warning(f"Threads cookie fetch failed: {e}")
            
    # Extract scripts
    scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
    
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
        # Fallback search
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
        # Check if auth/login is required
        if "login" in final_url.lower() or "Confirm you're not a bot".lower() in html.lower():
            return {
                "status": "error",
                "message": "Threads requires identity verification or this is a private post. Please export and upload a J2TEAM cookie file (Netscape or JSON format) for Instagram/Threads to continue."
            }
        return {"status": "error", "message": "Unable to extract post information from this Threads page. The post may have been deleted or access is restricted."}
        
    # Extract info from target_post
    uploader = target_post.get("user", {}).get("username", "Threads User")
    uploader_pic = target_post.get("user", {}).get("profile_pic_url", "")
    caption_text = target_post.get("caption", {}).get("text", "")
    likes = target_post.get("like_count", 0)
    
    media_type = target_post.get("media_type") # 1: Image, 2: Video, 8: Carousel
    
    video_options = []
    images = []
    
    # Process images helper
    def extract_image_url(image_versions2):
        if not image_versions2:
            return None
        candidates = image_versions2.get("candidates", [])
        if candidates:
            candidates = sorted(candidates, key=lambda x: x.get("width", 0), reverse=True)
            return candidates[0].get("url")
        return None

    # Extract duration_sec
    duration_sec = target_post.get("video_duration")
    if duration_sec is None:
        if media_type == 8:
            carousel_media = target_post.get("carousel_media", []) or []
            for item in carousel_media:
                if item.get("video_duration"):
                    duration_sec = item.get("video_duration")
                    break
    if duration_sec is not None:
        try:
            duration_sec = float(duration_sec)
        except Exception:
            duration_sec = 15.0
    else:
        duration_sec = 0.0

    if media_type == 8: # Carousel
        carousel_media = target_post.get("carousel_media", []) or []
        for idx, item in enumerate(carousel_media):
            img_url = extract_image_url(item.get("image_versions2"))
            if img_url:
                images.append({
                    "label": f"Slide Photo {idx+1}",
                    "url": img_url,
                    "ext": "jpg"
                })
                video_options.append({
                    "format_id": f"direct_photo_slide_{idx+1}",
                    "resolution": "Original",
                    "ext": "jpg",
                    "type": "image",
                    "size": "Unknown Size",
                    "label": f"Photo - Slide {idx+1}",
                    "url": img_url
                })
            
            # If video slide
            video_versions = item.get("video_versions", [])
            if video_versions:
                video_versions = sorted(video_versions, key=lambda x: x.get("width", 0), reverse=True)
                v_url = video_versions[0].get("url")
                video_options.append({
                    "format_id": f"direct_video_slide_{idx+1}",
                    "ext": "mp4",
                    "resolution": f"Slide {idx+1}",
                    "type": "video",
                    "size": "Unknown Size",
                    "label": f"Video Slide {idx+1}",
                    "url": v_url
                })
                if not duration_sec and item.get("video_duration"):
                    try:
                        duration_sec = float(item.get("video_duration"))
                    except Exception:
                        pass
    elif media_type == 2 or target_post.get("video_versions"): # Video
        video_versions = target_post.get("video_versions", [])
        if video_versions:
            video_versions = sorted(video_versions, key=lambda x: x.get("width", 0), reverse=True)
            v_url = video_versions[0].get("url")
            video_options.append({
                "format_id": "direct_video_original",
                "ext": "mp4",
                "resolution": "Original",
                "type": "video",
                "size": "Unknown Size",
                "label": "Video (Original)",
                "url": v_url
            })
            if not duration_sec:
                duration_sec = 15.0
        
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
            video_options.append({
                "format_id": "direct_photo_original",
                "resolution": "Original",
                "ext": "jpg",
                "type": "image",
                "size": "Unknown Size",
                "label": "Photo (Original)",
                "url": img_url
            })
            
    # If it is text only
    if not images and not video_options:
        return {
            "status": "error",
            "message": "This Threads post only contains text and does not have any images or videos to download."
        }
        
    thumbnail = images[0]["url"] if images else ""
    
    # Generate audio extraction options if video exists
    audio_options = []
    only_videos = [opt for opt in video_options if opt.get("type") == "video"]
    if only_videos and not duration_sec:
        duration_sec = 15.0
        
    if only_videos:
        audio_options.append({
            "format_id": "direct_video_audio_m4a",
            "resolution": "Audio",
            "ext": "m4a",
            "type": "audio",
            "size": "Unknown Size",
            "label": "M4A AAC (Original Quality - Fast)",
            "url": only_videos[0]["url"]
        })
        for q_val, q_name, q_label in [("320", "Ultra", "320kbps"), ("192", "High", "192kbps"), ("128", "Standard", "128kbps")]:
            audio_options.append({
                "format_id": "direct_video_audio_mp3",
                "resolution": "Audio",
                "ext": "mp3",
                "type": "audio",
                "quality": q_val,
                "size": "Unknown Size",
                "label": f"MP3 {q_name} ({q_label})",
                "url": only_videos[0]["url"]
            })
            
    from utils.cookies import get_cookie_file_path
    client_cookies = get_cookie_file_path(client_id) if client_id else None
    
    def resolve_threads_size(opt):
        url_to_check = opt.get("url")
        if url_to_check:
            s_bytes = get_url_content_length(url_to_check, cookies_file=client_cookies)
            if s_bytes:
                opt["size"] = format_size(s_bytes)

    if video_options:
        with ThreadPoolExecutor(max_workers=min(10, len(video_options))) as executor:
            list(executor.map(resolve_threads_size, video_options))

    # Estimate audio sizes using duration_sec
    if duration_sec:
        for opt in audio_options:
            if opt["ext"] == "m4a":
                opt["size"] = format_size(int(duration_sec * 128 * 1000 / 8))
            elif opt["ext"] == "mp3":
                q_val = opt.get("quality", "128")
                opt["size"] = format_size(int(duration_sec * int(q_val) * 1000 / 8))

    result = {
        "status": "success",
        "title": caption_text[:80] + "..." if len(caption_text) > 80 else (caption_text or "Threads Post"),
        "duration": format_duration(duration_sec) if duration_sec else "0:00",
        "uploader": uploader,
        "uploader_pic": uploader_pic,
        "thumbnail": thumbnail,
        "views": "N/A",
        "likes": f"{likes:,}" if likes else "0",
        "upload_date": "Today",
        "category": "Threads Post",
        "tags": ["Threads"],
        "subtitles": [],
        "video_options": video_options,
        "audio_options": audio_options,
        "images": images,
        "platform": "Threads",
        "platform_class": "threads",
        "platform_label": "Threads"
    }
    return result
