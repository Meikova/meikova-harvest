import os
import json
import logging
import re
import html
import requests
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from config import TEMP_DOWNLOAD_DIR
from utils.helpers import get_url_content_length, format_size, format_duration, format_number

logger = logging.getLogger(__name__)

def extract_reddit_via_gallery_dl(url, client_id):
    """
    Invokes gallery-dl via subprocess to extract Reddit photo/video posts.
    Reuses the client's uploaded J2TEAM cookies if available.
    """
    # Locate gallery-dl executable
    gallery_dl_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venv", "Scripts", "gallery-dl.exe")
    if not os.path.exists(gallery_dl_path):
        gallery_dl_path = "gallery-dl"
        
    command = [gallery_dl_path, "--dump-json"]
    
    # Check if a client-specific cookies file exists
    client_cookies = None
    if client_id:
        client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")
        if os.path.exists(client_cookies):
            command.extend(["--cookies", client_cookies])
            logger.info(f"gallery-dl (Reddit): Using client cookies file: {client_cookies}")
            
    command.append(url)
    
    try:
        logger.info(f"Invoking gallery-dl for Reddit: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        
        stdout = result.stdout.strip()
        if not stdout:
            logger.warning(f"gallery-dl (Reddit) returned empty output. Stderr: {result.stderr}")
            return None
            
        # Parse output
        entries = []
        try:
            data = json.loads(stdout)
            if isinstance(data, list):
                if data and isinstance(data[0], list):
                    for item in data:
                        if isinstance(item, list):
                            entries.append(item)
                else:
                    entries = [data]
        except Exception as json_e:
            logger.info(f"Failed to parse entire gallery-dl (Reddit) stdout as JSON: {json_e}")
            lines = stdout.splitlines()
            for line in lines:
                if line.strip().startswith("["):
                    try:
                        entry = json.loads(line)
                        if isinstance(entry, list):
                            entries.append(entry)
                    except Exception as parse_e:
                        logger.warning(f"Failed to parse Reddit line: {line}. Error: {parse_e}")

        # Check for errors in entries
        valid_entries = []
        for entry in entries:
            if len(entry) >= 2 and isinstance(entry[1], dict) and "error" in entry[1]:
                err_msg = entry[1].get("message", "")
                logger.warning(f"gallery-dl (Reddit) returned error: {err_msg}")
                if any(k in err_msg.lower() for k in ["login", "redirect", "cookie", "security", "blocked"]):
                    raise Exception("Reddit login required")
                continue
            valid_entries.append(entry)
            
        entries = valid_entries
        if not entries:
            return None
            
        # Extract metadata from the first entry
        first_metadata = {}
        for entry in entries:
            if len(entry) == 2 and isinstance(entry[1], dict):
                first_metadata = entry[1]
                break
            elif len(entry) >= 3 and isinstance(entry[2], dict):
                first_metadata = entry[2]
                break
                
        uploader = first_metadata.get("author") or "Reddit User"
        subreddit = first_metadata.get("subreddit") or "reddit"
        title = first_metadata.get("title") or f"Reddit Post by {uploader}"
        if len(title) > 80:
            title = title[:80] + "..."
            
        description = first_metadata.get("content") or first_metadata.get("description") or f"Subreddit: r/{subreddit}"
        
        # Stats
        views = first_metadata.get("view_count") or "N/A"
        likes = first_metadata.get("ups") or first_metadata.get("score") or "N/A"
        likes = format_number(int(likes)) if likes != "N/A" else "N/A"
        
        # Format date
        raw_date = first_metadata.get("created_utc")
        upload_date = "Unknown Date"
        if raw_date:
            try:
                dt = datetime.fromtimestamp(float(raw_date))
                upload_date = dt.strftime("%d %b %Y")
            except Exception:
                upload_date = str(raw_date)
                
        images = []
        video_options = []
        audio_options = []
        
        slide_num = 0
        thumbnail = None
        duration_sec = 0.0
        
        for entry in entries:
            if len(entry) < 3 or not isinstance(entry[1], str):
                continue
            media_url = entry[1]
            meta = entry[2] if len(entry) >= 3 and isinstance(entry[2], dict) else {}
            
            # Skip redirect entries
            if meta.get("subcategory") == "redirect" or meta.get("type") == "redirect":
                continue
            
            ext = meta.get("extension") or "jpg"
            # Reddit video files usually have .mp4 or m3u8
            is_video = ".mp4" in media_url.lower() or meta.get("type") == "video" or "v.redd.it" in media_url.lower()
            if is_video:
                ext = "mp4"
                
            slide_num += 1
            if not thumbnail:
                raw_thumb = first_metadata.get("thumbnail", "")
                if raw_thumb and raw_thumb.startswith("http"):
                    thumbnail = raw_thumb
                else:
                    thumbnail = media_url
                
            if ext == "mp4":
                # Video item
                d_val = meta.get("duration")
                if d_val:
                    try:
                        duration_sec = max(duration_sec, float(d_val))
                    except Exception:
                        pass
                video_options.append({
                    "format_id": f"direct_video_slide_{slide_num}",
                    "resolution": "HD",
                    "ext": "mp4",
                    "type": "video",
                    "size": "Unknown Size",
                    "label": f"Video Slide {slide_num}",
                    "url": media_url
                })
                # Add audio options
                audio_options.append({
                    "format_id": f"direct_audio_slide_{slide_num}_m4a",
                    "resolution": "Audio",
                    "ext": "m4a",
                    "type": "audio",
                    "size": "Unknown Size",
                    "label": f"M4A Audio Slide {slide_num} (128kbps)",
                    "url": media_url
                })
                audio_options.append({
                    "format_id": f"direct_audio_slide_{slide_num}_mp3",
                    "resolution": "Audio",
                    "ext": "mp3",
                    "type": "audio",
                    "size": "Unknown Size",
                    "label": f"MP3 Audio Slide {slide_num} (192kbps)",
                    "url": media_url
                })
            else:
                # Photo item
                images.append({
                    "label": f"Photo {slide_num}",
                    "url": media_url,
                    "ext": "jpg"
                })
                video_options.append({
                    "format_id": f"direct_photo_slide_{slide_num}",
                    "resolution": f"{meta.get('width', 0)}x{meta.get('height', 0)}" if meta.get("width") else "Original",
                    "ext": "jpg",
                    "type": "image",
                    "size": "Unknown Size",
                    "label": f"Photo {slide_num}",
                    "url": media_url
                })
                
        # Estimate audio sizes
        if duration_sec:
            for opt in audio_options:
                q_val = "128"
                if "mp3" in opt.get("format_id", "").lower():
                    q_val = "192"
                try:
                    opt["size"] = format_size(int(duration_sec * int(q_val) * 1000 / 8))
                except Exception:
                    pass
                    
        # Resolve sizes in parallel
        def resolve_size(opt):
            url_to_check = opt.get("url")
            if url_to_check:
                size_bytes = get_url_content_length(url_to_check, client_cookies)
                if size_bytes:
                    opt["size"] = format_size(size_bytes)
                    
        if video_options:
            with ThreadPoolExecutor(max_workers=min(10, len(video_options))) as executor:
                list(executor.map(resolve_size, video_options))
                
        # Fix thumbnail if it's a video file or Reddit placeholder string
        if thumbnail and not thumbnail.startswith("http"):
            thumbnail = None
        if thumbnail and (".mp4" in thumbnail.lower() or "self" in thumbnail.lower() or "default" in thumbnail.lower() or "image" == thumbnail.lower() or "nsfw" == thumbnail.lower() or "spoiler" == thumbnail.lower()):
            thumbnail = None
            
        return {
            "status": "success",
            "title": title,
            "uploader": uploader,
            "duration": format_duration(duration_sec) if duration_sec else "0:00",
            "thumbnail": thumbnail,
            "is_shorts": False,
            "platform_label": "Reddit",
            "platform_class": "reddit",
            "views": views,
            "likes": likes,
            "upload_date": upload_date,
            "description": description,
            "category": f"r/{subreddit}",
            "tags": ["Reddit", subreddit],
            "video_options": video_options,
            "audio_options": audio_options,
            "subtitles": [],
            "images": images,
        }
    except Exception as e:
        logger.error(f"gallery-dl Reddit extraction error: {e}")
        if "login" in str(e).lower() or "security" in str(e).lower() or "blocked" in str(e).lower():
            raise e
        return None


def scrape_reddit_fallback(url, client_id=None):
    """
    Fallback scraper for Reddit posts using old.reddit.com HTML.
    Bypasses Cloudflare block on www.reddit.com API endpoints.
    """
    cookies_dict = {}
    client_cookies = None
    if client_id:
        client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")
        if os.path.exists(client_cookies):
            try:
                with open(client_cookies, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        parts = line.split('\t')
                        if len(parts) >= 7:
                            cookies_dict[parts[5]] = parts[6]
            except Exception as cookie_err:
                logger.warning(f"Failed to parse cookies for Reddit fallback: {cookie_err}")

    # Normalize to old.reddit.com and strip query parameters
    m = re.match(r"https?://(?:www\.|old\.|new\.|embed\.)?reddit\.com/(r/[^/]+/comments/[^/]+/[^/]+)", url)
    if not m:
        # Check for redd.it short link
        m2 = re.match(r"https?://redd\.it/([^/?]+)", url)
        # Check for Reddit share link format: reddit.com/r/xxx/s/xxx
        m3 = re.match(r"https?://(?:www\.|old\.|new\.)?reddit\.com/(r/[^/]+/s/[^/?]+)", url) if not m2 else None
        
        if m2 or m3:
            resolve_url = url
            if m2:
                post_id = m2.group(1)
                resolve_url = f"https://old.reddit.com/{post_id}"
            
            # Fetch to resolve redirect
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            try:
                res = requests.get(resolve_url, headers=headers, cookies=cookies_dict, timeout=15, allow_redirects=True)
                url = res.url
                logger.info(f"Reddit share/short link resolved to: {url}")
                m = re.match(r"https?://(?:www\.|old\.|new\.|embed\.)?reddit\.com/(r/[^/]+/comments/[^/]+/[^/]+)", url)
            except Exception as e:
                logger.warning(f"Failed to resolve Reddit short/share URL: {e}")
                return None
        else:
            return None

    path = m.group(1)
    old_url = f"https://old.reddit.com/{path}/"
    logger.info(f"Reddit Fallback: Scraping HTML from {old_url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    try:
        res = requests.get(old_url, headers=headers, cookies=cookies_dict, timeout=15)
        if res.status_code != 200:
            logger.warning(f"Reddit Fallback request failed with status code {res.status_code}")
            return None
            
        html_content = res.text
        if "verification" in html_content.lower() and "captcha" in html_content.lower():
            logger.warning("Reddit Fallback: Hit verification/captcha block even on old.reddit.com")
            return None

        # Parse title
        title = "Reddit Post"
        title_m = re.search(r'<title>(.*?)</title>', html_content)
        if title_m:
            title = title_m.group(1).strip()
            title = re.sub(r"\s*:\s*\w+$", "", title)
            title = html.unescape(title)
            
        # Parse subreddit
        subreddit = "reddit"
        sub_url_m = re.search(r"/r/([^/]+)/comments/", url)
        if sub_url_m:
            subreddit = sub_url_m.group(1)
            
        # Parse author
        author = "Reddit User"
        author_m = re.search(r'class="[^"]*author[^"]*"[^>]*>(.*?)</a>', html_content)
        if author_m:
            author = author_m.group(1)
            
        # Find all media IDs in gallery
        media_ids = {} # maps id -> ext
        
        # Look for preview/direct links in HTML
        preview_links = re.findall(r'https?://preview\.redd\.it/([^./?]+)\.([^/?"]+)', html_content)
        for media_id, ext in preview_links:
            ext = ext.split("&")[0].split("?")[0]
            if len(media_id) > 5:
                media_ids[media_id] = ext
                
        direct_links = re.findall(r'https?://i\.redd\.it/([^./?]+)\.([^/?"]+)', html_content)
        for media_id, ext in direct_links:
            ext = ext.split("&")[0].split("?")[0]
            if len(media_id) > 5:
                media_ids[media_id] = ext
                
        logger.info(f"Reddit Fallback: Found media IDs: {media_ids}")
        
        images = []
        video_options = []
        audio_options = []
        
        slide_num = 0
        thumbnail = None
        
        for media_id, ext in media_ids.items():
            slide_num += 1
            direct_url = f"https://i.redd.it/{media_id}.{ext}"
            
            if not thumbnail:
                thumbnail = f"https://preview.redd.it/{media_id}.jpg?width=320&crop=smart&auto=webp"
                
            if ext.lower() == "gif":
                images.append({
                    "label": f"GIF {slide_num}",
                    "url": direct_url,
                    "ext": "gif"
                })
                mp4_url = f"https://preview.redd.it/{media_id}.gif?format=mp4"
                video_options.append({
                    "format_id": f"direct_video_slide_{slide_num}",
                    "resolution": "GIF/MP4",
                    "ext": "mp4",
                    "type": "video",
                    "size": "Unknown Size",
                    "label": f"Animated GIF {slide_num}",
                    "url": mp4_url
                })
            else:
                images.append({
                    "label": f"Photo {slide_num}",
                    "url": direct_url,
                    "ext": ext
                })
                video_options.append({
                    "format_id": f"direct_photo_slide_{slide_num}",
                    "resolution": "Original",
                    "ext": ext,
                    "type": "image",
                    "size": "Unknown Size",
                    "label": f"Photo {slide_num}",
                    "url": direct_url
                })
                
        # Look for single video post (v.redd.it)
        v_reddit_m = re.search(r'https?://v\.redd\.it/([^/\s"]+)', html_content)
        if v_reddit_m:
            video_id = v_reddit_m.group(1)
            logger.info(f"Reddit Fallback: Detected v.redd.it video ID: {video_id}")
            hls_url = f"https://v.redd.it/{video_id}/HLSPlaylist.m3u8"
            video_options.append({
                "format_id": "reddit_hls",
                "resolution": "Multi",
                "ext": "mp4",
                "type": "video",
                "size": "Unknown Size",
                "label": "HLS Playlist (Video + Audio)",
                "url": hls_url
            })
            resolutions = ["1080", "720", "480", "360", "240"]
            for res_val in resolutions:
                video_options.append({
                    "format_id": f"reddit_dash_{res_val}",
                    "resolution": f"{res_val}p",
                    "ext": "mp4",
                    "type": "video",
                    "size": "Unknown Size",
                    "label": f"Direct Video ({res_val}p)",
                    "url": f"https://v.redd.it/{video_id}/DASH_{res_val}.mp4"
                })
            audio_options.append({
                "format_id": "reddit_audio",
                "resolution": "Audio",
                "ext": "m4a",
                "type": "audio",
                "size": "Unknown Size",
                "label": "Reddit Video Audio",
                "url": f"https://v.redd.it/{video_id}/DASH_AUDIO_128.mp4"
            })
            thumb_m = re.search(r'<meta property="og:image" content="([^"]+)"', html_content)
            if thumb_m:
                thumbnail = thumb_m.group(1)
                
        if not video_options and not images:
            logger.warning("Reddit Fallback: Scraped 0 media options.")
            return None
            
        # Resolve sizes in parallel
        def resolve_size(opt):
            url_to_check = opt.get("url")
            if url_to_check:
                size_bytes = get_url_content_length(url_to_check, client_cookies)
                if size_bytes:
                    opt["size"] = format_size(size_bytes)
                    
        with ThreadPoolExecutor(max_workers=min(10, len(video_options) + len(audio_options))) as executor:
            list(executor.map(resolve_size, video_options + audio_options))

        return {
            "status": "success",
            "title": title,
            "uploader": author,
            "duration": "0:00",
            "thumbnail": thumbnail,
            "is_shorts": False,
            "platform_label": "Reddit",
            "platform_class": "reddit",
            "views": "N/A",
            "likes": "N/A",
            "upload_date": "Unknown Date",
            "description": f"Subreddit: r/{subreddit}",
            "category": f"r/{subreddit}",
            "tags": ["Reddit", subreddit],
            "video_options": video_options,
            "audio_options": audio_options,
            "subtitles": [],
            "images": images,
        }
    except Exception as e:
        logger.error(f"Reddit Fallback scraper error: {e}")
        return None
