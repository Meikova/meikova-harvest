import os
import json
import logging
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from config import TEMP_DOWNLOAD_DIR
from utils.helpers import get_url_content_length, format_size, format_duration

logger = logging.getLogger(__name__)

def extract_tiktok_slideshow_via_gallery_dl(url, client_id):
    """
    Invokes gallery-dl via subprocess to extract TikTok slideshows.
    Reuses the client's uploaded cookies if available.
    """
    gallery_dl_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venv", "Scripts", "gallery-dl.exe")
    if not os.path.exists(gallery_dl_path):
        gallery_dl_path = "gallery-dl"
        
    # Strip query parameters to avoid 403 Forbidden and parser bugs in gallery-dl
    if "?" in url:
        url = url.split("?")[0]

    command = [gallery_dl_path, "--dump-json"]
    
    has_cookies = False
    if client_id:
        client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")
        if os.path.exists(client_cookies):
            command.extend(["--cookies", client_cookies])
            has_cookies = True
            logger.info(f"gallery-dl (TikTok): Using client cookies file: {client_cookies}")
            
    command.append(url)
    
    try:
        logger.info(f"Invoking gallery-dl for TikTok: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        
        # If extraction failed (empty stdout, empty list, or 403 error), retry without cookies
        should_retry = False
        if not stdout or stdout == "[]":
            should_retry = True
        elif "403" in stderr or "forbidden" in stderr.lower() or "error" in stderr.lower():
            should_retry = True
            
        if should_retry and has_cookies:
            logger.info("gallery-dl TikTok extraction failed with cookies. Retrying WITHOUT cookies...")
            fallback_command = [gallery_dl_path, "--dump-json", url]
            result = subprocess.run(fallback_command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            
        if not stdout or stdout == "[]":
            logger.warning(f"gallery-dl (TikTok) returned empty output. Stderr: {stderr}")
            return None
            
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
            logger.info(f"Failed to parse entire gallery-dl (TikTok) stdout as JSON: {json_e}")
            lines = stdout.splitlines()
            for line in lines:
                if line.strip().startswith("["):
                    try:
                        entry = json.loads(line)
                        if isinstance(entry, list):
                            entries.append(entry)
                    except Exception:
                        pass

        # Find the metadata entry (type 2)
        metadata = {}
        for entry in entries:
            if len(entry) >= 2 and isinstance(entry[1], dict) and entry[0] == 2:
                metadata = entry[1]
                break

        if not metadata:
            logger.warning(f"No metadata block found in gallery-dl (TikTok) output. stdout: {stdout[:1000]}, stderr: {result.stderr[:1000]}")
            return None

        # Check for errors
        if "error" in metadata:
            err_msg = metadata.get("message", "")
            logger.warning(f"gallery-dl TikTok error: {err_msg}")
            if any(k in err_msg.lower() for k in ["login", "redirect", "cookie", "captcha"]):
                raise Exception("TikTok verification / login required")
            return None

        # Author / Uploader info
        author = metadata.get("author") or {}
        uploader = author.get("nickname") or author.get("uniqueId") or metadata.get("user") or "TikTok User"
        
        # Title and description
        description = metadata.get("desc") or metadata.get("description") or ""
        title = description.split("\n")[0] if description else f"TikTok Slideshow by {uploader}"
        if len(title) > 80:
            title = title[:80] + "..."
            
        # Parse images from imagePost
        image_post = metadata.get("imagePost") or {}
        image_list = image_post.get("images") or []
        
        images = []
        video_options = []
        
        for idx, img in enumerate(image_list):
            img_url = None
            url_list = img.get("imageURL", {}).get("urlList") or []
            if url_list:
                img_url = url_list[0]
            if not img_url:
                continue
                
            width = img.get("imageWidth") or "Original"
            height = img.get("imageHeight") or ""
            resolution = f"{width}x{height}" if height else str(width)
            
            images.append({
                "label": f"Slide Photo {idx+1}",
                "url": img_url,
                "ext": "jpg"
            })
            
            video_options.append({
                "format_id": f"direct_photo_slide_{idx+1}",
                "resolution": resolution,
                "ext": "jpg",
                "type": "image",
                "size": "Unknown Size",
                "label": f"Photo - Slide {idx+1}",
                "url": img_url
            })
            
        # Audio track
        audio_options = []
        music = metadata.get("music") or {}
        music_url = music.get("playUrl")
        music_duration = music.get("duration") or 0
        
        if music_url:
            audio_options.append({
                "format_id": "direct_audio_tiktok_slideshow",
                "resolution": "Audio",
                "ext": "mp3",
                "type": "audio",
                "size": format_size(int(music_duration * 128 * 1000 / 8)) if music_duration else "Unknown Size",
                "label": f"Music: {music.get('title', 'Unknown')} - {music.get('authorName', 'Unknown')}",
                "url": music_url
            })
            
            audio_options.append({
                "format_id": "direct_audio_tiktok_slideshow_m4a",
                "resolution": "Audio",
                "ext": "m4a",
                "type": "audio",
                "size": format_size(int(music_duration * 128 * 1000 / 8)) if music_duration else "Unknown Size",
                "label": "M4A AAC (Original Quality - Fast)",
                "url": music_url
            })

        # Thumbnail
        cover_url_list = image_post.get("cover", {}).get("urlList") or []
        thumbnail = cover_url_list[0] if cover_url_list else (images[0]["url"] if images else "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=600")

        # Stats
        stats = metadata.get("stats") or {}
        likes_val = stats.get("diggCount")
        likes = "Unknown"
        if likes_val is not None:
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
                
        views_val = stats.get("playCount")
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

        # Upload date
        upload_date = "Unknown"
        create_time = metadata.get("createTime")
        if create_time:
            try:
                dt = datetime.fromtimestamp(int(create_time))
                upload_date = dt.strftime("%d %b %Y")
            except Exception:
                pass

        # Resolve sizes of photo options in parallel without cookies (to avoid 30s delays on CDN links)
        def resolve_size(opt):
            url_to_check = opt.get("url")
            if url_to_check:
                s_bytes = get_url_content_length(url_to_check, cookies_file=None)
                if s_bytes:
                    opt["size"] = format_size(s_bytes)

        if video_options:
            with ThreadPoolExecutor(max_workers=min(12, len(video_options))) as executor:
                list(executor.map(resolve_size, video_options))

        return {
            "status": "success",
            "title": title,
            "uploader": uploader,
            "duration": format_duration(music_duration) if music_duration else "0:00",
            "thumbnail": thumbnail,
            "is_shorts": False,
            "platform_label": "TikTok Slideshow",
            "platform_class": "tiktok-slideshow",
            "views": views,
            "likes": likes,
            "upload_date": upload_date,
            "description": description,
            "category": "TikTok Media",
            "tags": ["TikTok"],
            "video_options": video_options,
            "audio_options": audio_options,
            "subtitles": [],
            "images": images,
        }
    except Exception as e:
        logger.error(f"gallery-dl TikTok slideshow extraction error: {e}")
        if "login" in str(e).lower() or "verification" in str(e).lower() or "cookie" in str(e).lower():
            raise e
        return None
