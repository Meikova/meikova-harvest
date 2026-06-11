import os
import json
import logging
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from config import TEMP_DOWNLOAD_DIR
from utils.helpers import get_url_content_length, format_size, format_duration

logger = logging.getLogger(__name__)

def extract_instagram_via_gallery_dl(url, client_id):
    """
    Invokes gallery-dl via subprocess to extract Instagram photo/video posts.
    Reuses the client's uploaded J2TEAM cookies if available.
    """
    # Locate gallery-dl executable
    gallery_dl_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venv", "Scripts", "gallery-dl.exe")
    if not os.path.exists(gallery_dl_path):
        gallery_dl_path = "gallery-dl" # Fallback to path
        
    command = [gallery_dl_path, "--dump-json"]
    
    # Check if a client-specific cookies file exists
    if client_id:
        client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")
        if os.path.exists(client_cookies):
            command.extend(["--cookies", client_cookies])
            logger.info(f"gallery-dl: Using client cookies file: {client_cookies}")
            
    command.append(url)
    
    try:
        logger.info(f"Invoking gallery-dl: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        
        stdout = result.stdout.strip()
        if not stdout:
            logger.warning(f"gallery-dl returned empty output. Stderr: {result.stderr}")
            return None
            
        # Parse output
        entries = []
        try:
            # Try parsing the entire stdout as a single JSON array
            data = json.loads(stdout)
            if isinstance(data, list):
                if data and isinstance(data[0], list):
                    # It's a list of entries
                    for item in data:
                        if isinstance(item, list):
                            entries.append(item)
                else:
                    # It's a single entry list
                    entries = [data]
        except Exception as json_e:
            logger.info(f"Failed to parse entire gallery-dl stdout as JSON: {json_e}. Falling back to line-by-line parsing.")
            lines = stdout.splitlines()
            for line in lines:
                if line.strip().startswith("["):
                    try:
                        entry = json.loads(line)
                        if isinstance(entry, list):
                            entries.append(entry)
                    except Exception as parse_e:
                        logger.warning(f"Failed to parse line: {line}. Error: {parse_e}")

        # Check for errors in entries
        valid_entries = []
        for entry in entries:
            if len(entry) >= 2 and isinstance(entry[1], dict) and "error" in entry[1]:
                err_msg = entry[1].get("message", "")
                logger.warning(f"gallery-dl returned error: {err_msg}")
                if any(k in err_msg.lower() for k in ["login", "redirect", "cookie"]):
                    raise Exception("Instagram login required")
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
                
        uploader = first_metadata.get("username") or first_metadata.get("owner") or "Instagram User"
        if isinstance(uploader, dict):
            uploader = uploader.get("username") or uploader.get("name") or "Instagram User"
            
        caption = first_metadata.get("caption") or first_metadata.get("description") or ""
        
        # Clean caption for title
        title = caption.split("\n")[0] if caption else f"Instagram Post by {uploader}"
        if len(title) > 80:
            title = title[:80] + "..."
            
        description = caption or "No description available."
        
        images = []
        video_options = []
        audio_options = []
        
        is_story = "/stories/" in url.lower()
        unit_label = "Story" if is_story else "Slide"
        
        duration_sec = 0.0
        slide_num = 0
        for entry in entries:
            if len(entry) < 3 or not isinstance(entry[1], str):
                continue
            media_url = entry[1]
            meta = entry[2] if len(entry) >= 3 and isinstance(entry[2], dict) else {}
            
            # Skip redirect entries
            if meta.get("subcategory") == "redirect" or meta.get("type") == "redirect":
                continue
            
            # Get duration
            try:
                for k in ["audio_duration", "duration", "video_duration"]:
                    d_val = meta.get(k)
                    if d_val is not None:
                        duration_sec = max(duration_sec, float(d_val))
            except Exception:
                pass

            # Determine extension
            ext = "jpg"
            if ".mp4" in media_url.lower() or meta.get("media_type") == 2:
                ext = "mp4"
                
            slide_num += 1
            
            if ext == "mp4":
                # Use direct video URL from metadata if available to avoid ytdl: placeholder
                v_url = meta.get("video_url") or media_url
                if isinstance(v_url, str) and v_url.startswith("ytdl:") and meta.get("video_url"):
                    v_url = meta.get("video_url")
                
                # Try to get clean resolution height
                height = meta.get("height") or meta.get("height_original")
                res_label = f"{height}p" if isinstance(height, int) else "HD"
                
                video_options.append({
                    "format_id": f"direct_video_slide_{slide_num}",
                    "resolution": res_label,
                    "ext": "mp4",
                    "type": "video",
                    "size": "Unknown Size",
                    "label": f"Video {unit_label} {slide_num} ({res_label})",
                    "url": v_url
                })
                # Add default video thumbnail placeholder
                t_url = meta.get("display_url") or media_url
                if isinstance(t_url, str) and t_url.startswith("ytdl:") and meta.get("display_url"):
                    t_url = meta.get("display_url")
                images.append({
                    "label": f"{unit_label} {slide_num} Video Thumbnail",
                    "url": t_url,
                    "ext": "jpg"
                })
            else:
                images.append({
                    "label": f"{unit_label} {slide_num} Image",
                    "url": media_url,
                    "ext": "jpg"
                })
                video_options.append({
                    "format_id": f"direct_photo_slide_{slide_num}",
                    "resolution": "Original",
                    "ext": "jpg",
                    "type": "image",
                    "size": "Unknown Size",
                    "label": f"Photo - {unit_label} {slide_num}",
                    "url": media_url
                })
                
        thumbnail = images[0]["url"] if images else "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=600"
        
        # Classify sub-platform
        platform_label = "Instagram Post"
        platform_class = "instagram-post"
        if "/reel/" in url or "/reels/" in url:
            platform_label = "Instagram Reel"
            platform_class = "instagram-reel"
        elif "/stories/" in url:
            platform_label = "Instagram Story"
            platform_class = "instagram-story"
        elif "/tv/" in url:
            platform_label = "Instagram TV"
            platform_class = "instagram-tv"
            
        # Extract upload date
        upload_date = "Unknown"
        raw_date = first_metadata.get("post_date") or first_metadata.get("date")
        if raw_date:
            try:
                dt = datetime.strptime(raw_date.split(".")[0], "%Y-%m-%d %H:%M:%S")
                upload_date = dt.strftime("%d %b %Y")
            except Exception:
                upload_date = raw_date.split(" ")[0] if " " in raw_date else raw_date

        # Extract likes
        likes_val = first_metadata.get("likes")
        likes = "N/A" if is_story else "Unknown"
        if likes_val is not None and not is_story:
            try:
                likes_count = int(likes_val)
                if likes_count >= 1_000_000:
                    likes = f"{likes_count / 1_000_000:.1f}M"
                elif likes_count >= 1_000:
                    likes = f"{likes_count / 1_000:.1f}K"
                else:
                    likes = str(likes_count)
            except Exception:
                likes = str(likes_val)

        # Extract views
        views_val = first_metadata.get("views") or first_metadata.get("view_count")
        views = "N/A"
        has_video_slides = any(".mp4" in entry[1].lower() or (len(entry) >= 3 and isinstance(entry[2], dict) and entry[2].get("media_type") == 2) for entry in entries if len(entry) >= 3 and isinstance(entry[1], str))
        if has_video_slides and not is_story:
            views = "Unknown"
            
        if views_val is not None:
            try:
                views_count = int(views_val)
                if views_count >= 1_000_000:
                    views = f"{views_count / 1_000_000:.1f}M"
                elif views_count >= 1_000:
                    views = f"{views_count / 1_000:.1f}K"
                else:
                    views = str(views_count)
            except Exception:
                views = str(views_val)
        # Generate audio extraction options if video exists
        if video_options:
            only_videos = [opt for opt in video_options if opt.get("ext") == "mp4"]
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

        # Resolve sizes of video_options in parallel using ThreadPoolExecutor
        client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt") if client_id else None
        
        def resolve_size(opt):
            url_to_check = opt.get("url")
            if url_to_check:
                s_bytes = get_url_content_length(url_to_check, cookies_file=client_cookies)
                if s_bytes:
                    opt["size"] = format_size(s_bytes)

        if video_options:
            with ThreadPoolExecutor(max_workers=min(10, len(video_options))) as executor:
                list(executor.map(resolve_size, video_options))

        # Estimate audio sizes using duration_sec
        if duration_sec:
            for opt in audio_options:
                if opt["ext"] == "m4a":
                    opt["size"] = format_size(int(duration_sec * 128 * 1000 / 8))
                elif opt["ext"] == "mp3":
                    q_val = opt.get("quality", "128")
                    opt["size"] = format_size(int(duration_sec * int(q_val) * 1000 / 8))

        return {
            "status": "success",
            "title": title,
            "uploader": uploader,
            "duration": format_duration(duration_sec) if duration_sec else "0:00",
            "thumbnail": thumbnail,
            "is_shorts": False,
            "platform_label": platform_label,
            "platform_class": platform_class,
            "views": views,
            "likes": likes,
            "upload_date": upload_date,
            "description": description,
            "category": "Instagram Media",
            "tags": ["Instagram"],
            "video_options": video_options,
            "audio_options": audio_options,
            "subtitles": [],
            "images": images,
        }
    except Exception as e:
        logger.error(f"gallery-dl extraction error: {e}")
        if "login" in str(e).lower():
            raise e
        return None
