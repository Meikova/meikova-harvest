import os
import json
import logging
import re
import subprocess
import urllib.request
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from config import TEMP_DOWNLOAD_DIR
from utils.helpers import get_url_content_length, format_size, format_duration, format_number, get_gallery_dl_path

logger = logging.getLogger(__name__)

def extract_twitter_video_thumbnail_from_html(url):
    """
    Attempts to scrape the actual Twitter video thumbnail/poster image URL from the page HTML.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://x.com/"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as res:
            html_content = res.read().decode("utf-8", errors="ignore")
            # Search for amplify_video_thumb or ext_tw_video_thumb or media
            match = re.search(r'https://pbs\.twimg\.com/(?:amplify_video_thumb|ext_tw_video_thumb|media)/[^\s"\']+', html_content)
            if match:
                return match.group(0)
    except Exception as e:
        logger.warning(f"Failed to scrape Twitter video thumbnail from HTML: {e}")
    return None


def extract_twitter_via_gallery_dl(url, client_id):
    """
    Invokes gallery-dl via subprocess to extract Twitter/X photo/video posts.
    Reuses the client's uploaded J2TEAM cookies if available.
    """
    # Locate gallery-dl executable
    gallery_dl_path = get_gallery_dl_path()
        
    command = [gallery_dl_path, "--dump-json"]
    
    # Check if a client-specific cookies file exists
    if client_id:
        client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")
        if os.path.exists(client_cookies):
            command.extend(["--cookies", client_cookies])
            logger.info(f"gallery-dl (Twitter): Using client cookies file: {client_cookies}")
            
    command.append(url)
    
    try:
        logger.info(f"Invoking gallery-dl for Twitter/X: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=15)
        
        stdout = result.stdout.strip()
        if not stdout:
            logger.warning(f"gallery-dl (Twitter) returned empty output. Stderr: {result.stderr}")
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
            logger.info(f"Failed to parse entire gallery-dl (Twitter) stdout as JSON: {json_e}")
            lines = stdout.splitlines()
            for line in lines:
                if line.strip().startswith("["):
                    try:
                        entry = json.loads(line)
                        if isinstance(entry, list):
                            entries.append(entry)
                    except Exception as parse_e:
                        logger.warning(f"Failed to parse Twitter line: {line}. Error: {parse_e}")

        # Check for errors in entries
        valid_entries = []
        for entry in entries:
            if len(entry) >= 2 and isinstance(entry[1], dict) and "error" in entry[1]:
                err_msg = entry[1].get("message", "")
                logger.warning(f"gallery-dl (Twitter) returned error: {err_msg}")
                if any(k in err_msg.lower() for k in ["login", "redirect", "cookie"]):
                    raise Exception("Twitter login required")
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
                
        # Handle Twitter-specific metadata keys
        user_info = first_metadata.get("user") or {}
        uploader = user_info.get("nick") or user_info.get("name") or first_metadata.get("author", {}).get("nick") or "Twitter User"
        content = first_metadata.get("content") or first_metadata.get("description") or ""
        
        title = content.split("\n")[0] if content else f"Tweet by {uploader}"
        if len(title) > 80:
            title = title[:80] + "..."
            
        description = content or "No description available."
        
        # Format date
        raw_date = first_metadata.get("date")
        upload_date = "Unknown Date"
        if raw_date:
            try:
                dt = datetime.strptime(raw_date.split(".")[0], "%Y-%m-%d %H:%M:%S")
                upload_date = dt.strftime("%d %b %Y")
            except Exception:
                upload_date = raw_date
                
        # Stats
        views = first_metadata.get("view_count")
        views = format_number(int(views)) if views is not None else "N/A"
        likes = first_metadata.get("favorite_count")
        likes = format_number(int(likes)) if likes is not None else "N/A"
        
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
            
            # Determine extension
            ext = meta.get("extension") or "jpg"
            if ".mp4" in media_url.lower() or meta.get("type") == "video" or meta.get("type") == "gif":
                ext = "mp4"
                
            slide_num += 1
            if ext != "mp4" and not thumbnail:
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
                # Add video audio options (M4A and MP3)
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
                
        # Estimate audio sizes using duration_sec
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
        client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt") if client_id else None
        
        def resolve_size(opt):
            url_to_check = opt.get("url")
            if url_to_check:
                size_bytes = get_url_content_length(url_to_check, client_cookies)
                if size_bytes:
                    opt["size"] = format_size(size_bytes)
                    
        if video_options:
            with ThreadPoolExecutor(max_workers=min(10, len(video_options))) as executor:
                list(executor.map(resolve_size, video_options))
                
        # If it has a video and the thumbnail is None or avatar, attempt to scrape video thumbnail from HTML
        has_video_options = any(opt.get("type") == "video" for opt in video_options)
        if has_video_options and (not thumbnail or (user_info and thumbnail == user_info.get("profile_image"))):
            scraped_thumb = extract_twitter_video_thumbnail_from_html(url)
            if scraped_thumb:
                thumbnail = scraped_thumb
                logger.info(f"Successfully scraped Twitter video thumbnail from HTML: {thumbnail}")
                
        return {
            "status": "success",
            "title": title,
            "uploader": uploader,
            "duration": format_duration(duration_sec) if duration_sec else "0:00",
            "thumbnail": thumbnail or (user_info.get("profile_image") if user_info else None),
            "is_shorts": False,
            "platform_label": "Twitter/X",
            "platform_class": "twitter-x",
            "views": views,
            "likes": likes,
            "upload_date": upload_date,
            "description": description,
            "category": "Twitter/X Post",
            "tags": ["Twitter", "X"],
            "video_options": video_options,
            "audio_options": audio_options,
            "subtitles": [],
            "images": images,
        }
    except Exception as e:
        logger.error(f"gallery-dl Twitter extraction error: {e}")
        if any(k in str(e).lower() for k in ["login", "redirect", "cookie"]):
            raise e
        return None
