import os
import json
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor

from config import TEMP_DOWNLOAD_DIR
from utils.helpers import get_url_content_length, format_size, get_gallery_dl_path

logger = logging.getLogger(__name__)

def extract_pinterest_via_gallery_dl(url, client_id=None):
    """
    Invokes gallery-dl via subprocess to extract Pinterest photo/video posts.
    Reuses the client's uploaded J2TEAM cookies if available.
    """
    # Locate gallery-dl executable
    gallery_dl_path = get_gallery_dl_path()

    command = [gallery_dl_path, "--dump-json"]

    # Check if a client-specific cookies file exists
    client_cookies = None
    if client_id:
        client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")
        if os.path.exists(client_cookies):
            command.extend(["--cookies", client_cookies])
            logger.info(f"gallery-dl (Pinterest): Using client cookies file: {client_cookies}")

    command.append(url)

    try:
        logger.info(f"Invoking gallery-dl for Pinterest: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=15)

        stdout = result.stdout.strip()
        if not stdout:
            logger.warning(f"gallery-dl (Pinterest) returned empty output. Stderr: {result.stderr}")
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
            logger.info(f"Failed to parse entire gallery-dl (Pinterest) stdout as JSON: {json_e}")
            lines = stdout.splitlines()
            for line in lines:
                if line.strip().startswith("["):
                    try:
                        entry = json.loads(line)
                        if isinstance(entry, list):
                            entries.append(entry)
                    except Exception as parse_e:
                        logger.warning(f"Failed to parse Pinterest line: {line}. Error: {parse_e}")

        # Check for redirects or errors in entries
        valid_entries = []
        redirect_url = None
        for entry in entries:
            if entry[0] == 6 and isinstance(entry[1], str):
                redirect_url = entry[1]
                break
            if len(entry) >= 2 and isinstance(entry[1], dict) and "error" in entry[1]:
                err_msg = entry[1].get("message", "")
                logger.warning(f"gallery-dl (Pinterest) returned error: {err_msg}")
                continue
            valid_entries.append(entry)

        if redirect_url:
            logger.info(f"Pinterest redirect detected: {url} -> {redirect_url}")
            return extract_pinterest_via_gallery_dl(redirect_url, client_id)

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

        uploader = "Pinterest User"
        board_info = first_metadata.get("board")
        if isinstance(board_info, dict):
            owner_info = board_info.get("owner")
            if isinstance(owner_info, dict):
                uploader = owner_info.get("username") or owner_info.get("full_name") or owner_info.get("name") or "Pinterest User"
        
        if not uploader or uploader == "Pinterest User":
            uploader = first_metadata.get("username") or first_metadata.get("author") or "Pinterest User"

        title = first_metadata.get("title") or first_metadata.get("grid_title") or f"Pinterest Pin by {uploader}"
        if len(title) > 80:
            title = title[:80] + "..."
            
        description = first_metadata.get("description") or first_metadata.get("content") or ""
        
        images = []
        video_options = []
        audio_options = []
        
        slide_num = 0
        thumbnail = None

        for entry in entries:
            if len(entry) < 3 or not isinstance(entry[1], str):
                continue
            media_url = entry[1]
            meta = entry[2] if len(entry) >= 3 and isinstance(entry[2], dict) else {}
            
            # Skip redirect entries
            if meta.get("subcategory") == "redirect" or meta.get("type") == "redirect" or entry[0] == 6:
                continue

            is_video = False
            videos_dict = meta.get("videos")
            v_url = None
            if isinstance(videos_dict, dict) and videos_dict:
                is_video = True
                best_video_key = None
                for vk in ["V_720P", "V_540P", "V_360P", "V_orig"]:
                    if vk in videos_dict:
                        best_video_key = vk
                        break
                if not best_video_key:
                    keys = list(videos_dict.keys())
                    if keys:
                        best_video_key = keys[0]
                if best_video_key:
                    v_url = videos_dict[best_video_key].get("url")
            elif ".mp4" in media_url.lower() or meta.get("type") == "video":
                is_video = True
                v_url = media_url

            slide_num += 1
            if not thumbnail:
                images_dict = meta.get("images")
                if isinstance(images_dict, dict) and "orig" in images_dict:
                    thumbnail = images_dict["orig"].get("url")
                else:
                    thumbnail = media_url

            if is_video and v_url:
                video_options.append({
                    "format_id": f"direct_video_slide_{slide_num}",
                    "resolution": "HD",
                    "ext": "mp4",
                    "type": "video",
                    "size": "Unknown Size",
                    "label": f"Video Slide {slide_num}",
                    "url": v_url
                })
            else:
                width = 0
                height = 0
                images_dict = meta.get("images")
                if isinstance(images_dict, dict) and "orig" in images_dict:
                    width = images_dict["orig"].get("width", 0)
                    height = images_dict["orig"].get("height", 0)
                
                images.append({
                    "label": f"Photo {slide_num}",
                    "url": media_url,
                    "ext": "jpg"
                })
                video_options.append({
                    "format_id": f"direct_photo_slide_{slide_num}",
                    "resolution": f"{width}x{height}" if width else "Original",
                    "ext": "jpg",
                    "type": "image",
                    "size": "Unknown Size",
                    "label": f"Photo {slide_num}",
                    "url": media_url
                })

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

        return {
            "status": "success",
            "title": title,
            "uploader": uploader,
            "duration": "0:00",
            "thumbnail": thumbnail,
            "is_shorts": False,
            "platform_label": "Pinterest",
            "platform_class": "pinterest",
            "views": "N/A",
            "likes": "N/A",
            "upload_date": "Unknown Date",
            "description": description,
            "category": "Pinterest Pin",
            "tags": ["Pinterest"],
            "video_options": video_options,
            "audio_options": audio_options,
            "subtitles": [],
            "images": images,
        }
    except Exception as e:
        logger.error(f"gallery-dl Pinterest extraction error: {e}")
        return None
