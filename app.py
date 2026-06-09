import os
import uuid
import shutil
import logging
import threading
from urllib.parse import quote
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
import yt_dlp
import static_ffmpeg

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Initialize static-ffmpeg to add portable binaries to PATH
logger.info("Initializing static-ffmpeg...")
try:
    static_ffmpeg.add_paths()
    logger.info("static-ffmpeg paths injected successfully.")
except Exception as e:
    logger.error(f"Failed to inject static-ffmpeg paths: {e}")

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

TEMP_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(TEMP_DOWNLOAD_DIR, exist_ok=True)

# Clean up any leftover temporary folders from previous runs on startup
logger.info("Cleaning up leftover temporary downloads...")
try:
    for item in os.listdir(TEMP_DOWNLOAD_DIR):
        if item == "cookies":
            continue
        item_path = os.path.join(TEMP_DOWNLOAD_DIR, item)
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
        else:
            os.remove(item_path)
    logger.info("Leftover temporary downloads cleaned (cookies preserved).")
except Exception as e:
    logger.warning(f"Failed to clean downloads directory on startup: {e}")

# Global dictionary for tracking download tasks
downloads_status = {}
downloads_status_lock = threading.Lock()

def schedule_cleanup(temp_dir, download_id, delay=300):
    """Schedules a delayed cleanup of the downloaded files to allow browser retries/fallback downloads."""
    def cleanup():
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Delayed cleanup completed for task {download_id} (purged {temp_dir})")
        except Exception as e:
            logger.error(f"Delayed cleanup error for task {download_id}: {e}")
        with downloads_status_lock:
            downloads_status.pop(download_id, None)

    timer = threading.Timer(delay, cleanup)
    timer.daemon = True
    timer.start()


def create_ydl_instance(ydl_opts, url=None, client_id=None):
    """
    Attempts to instantiate YoutubeDL. 
    If cookiesfrombrowser is 'auto', it will attempt different browsers one by one.
    If all fail, it will fall back to using no cookies.
    """
    # Check if a client-specific cookies file exists
    if client_id:
        client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")
        if os.path.exists(client_cookies):
            logger.info(f"Using client-specific cookies for client: {client_id}")
            opts = ydl_opts.copy()
            opts["cookiefile"] = client_cookies
            opts.pop("cookiesfrombrowser", None)
            try:
                return yt_dlp.YoutubeDL(opts)
            except Exception as e:
                logger.warning(f"Failed to load client cookies: {e}")

    # Check if a local cookies.txt file exists in the root folder
    local_cookies = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")
    if os.path.exists(local_cookies):
        logger.info("Using local default cookies.txt file")
        opts = ydl_opts.copy()
        opts["cookiefile"] = local_cookies
        opts.pop("cookiesfrombrowser", None)
        try:
            return yt_dlp.YoutubeDL(opts)
        except Exception as e:
            logger.warning(f"Failed to load local cookies.txt: {e}")

    if ydl_opts.get("cookiesfrombrowser") != "auto":
        return yt_dlp.YoutubeDL(ydl_opts)
        
    browsers = ["chrome", "edge", "firefox", "opera", "vivaldi", "brave"]
    
    # Extract target domain for cookie filtering
    target_domain = None
    if url:
        url_lower = url.lower()
        if "facebook" in url_lower or "fb.watch" in url_lower or "fb.gg" in url_lower or "fb.com" in url_lower:
            target_domain = "facebook"
        elif "youtube" in url_lower or "youtu.be" in url_lower:
            target_domain = "youtube"
        elif "instagram" in url_lower:
            target_domain = "instagram"
        elif "tiktok" in url_lower:
            target_domain = "tiktok"

    # Step 1: Prioritize browsers that have cookies for the target domain
    if target_domain:
        for browser in browsers:
            opts = ydl_opts.copy()
            opts["cookiesfrombrowser"] = (browser,)
            try:
                ydl = yt_dlp.YoutubeDL(opts)
                # Force loading of cookiejar and check for domain cookies
                cookiejar = ydl.cookiejar
                if any(target_domain in cookie.domain for cookie in cookiejar):
                    logger.info(f"Successfully loaded cookies from browser: {browser} (matched target domain '{target_domain}')")
                    return ydl
            except Exception:
                pass

    # Step 2: Fallback to the first browser that loads successfully (regardless of domain cookies)
    for browser in browsers:
        opts = ydl_opts.copy()
        opts["cookiesfrombrowser"] = (browser,)
        try:
            ydl = yt_dlp.YoutubeDL(opts)
            _ = ydl.cookiejar
            logger.info(f"Fallback to cookies from browser: {browser}")
            return ydl
        except Exception as e:
            logger.warning(f"Failed to load cookies from browser '{browser}': {e}")
            
    # Step 3: Fallback to no cookies if all failed
    opts = ydl_opts.copy()
    opts.pop("cookiesfrombrowser", None)
    logger.info("Falling back to YoutubeDL instance without cookies")
    return yt_dlp.YoutubeDL(opts)


@app.route("/")
def index():
    return render_template("index.html")


def parse_cookies_to_dict(content):
    cookies = {}
    stripped = content.strip()
    
    # Check if it's JSON
    if stripped.startswith("[") or stripped.startswith("{"):
        import json
        try:
            data = json.loads(stripped)
            cookies_list = None
            if isinstance(data, list):
                cookies_list = data
            elif isinstance(data, dict):
                cookies_list = data.get("cookies") or data.get("list") or []
                
            if isinstance(cookies_list, list):
                for cookie in cookies_list:
                    domain = cookie.get("domain", "")
                    if not domain:
                        continue
                    path = cookie.get("path", "/")
                    secure = "TRUE" if cookie.get("secure", False) else "FALSE"
                    expiration = str(int(cookie.get("expirationDate") or 0))
                    flag = "TRUE" if domain.startswith(".") else "FALSE"
                    name = cookie.get("name", "")
                    value = cookie.get("value", "")
                    key = (domain.lower(), path, name)
                    cookies[key] = {
                        "domain": domain,
                        "flag": flag,
                        "path": path,
                        "secure": secure,
                        "expiration": expiration,
                        "name": name,
                        "value": value
                    }
                return cookies
        except Exception as e:
            logger.warning(f"Failed to parse as JSON in parse_cookies_to_dict: {e}")
            
    # Fallback to Netscape format parser
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            domain = parts[0]
            flag = parts[1]
            path = parts[2]
            secure = parts[3]
            expiration = parts[4]
            name = parts[5]
            value = parts[6]
            key = (domain.lower(), path, name)
            cookies[key] = {
                "domain": domain,
                "flag": flag,
                "path": path,
                "secure": secure,
                "expiration": expiration,
                "name": name,
                "value": value
            }
    return cookies


def serialize_netscape_cookies(cookies_dict):
    lines = [
        "# Netscape HTTP Cookie File",
        "# http://curl.haxx.se/rfc/cookie_spec.html",
        "# This is a generated file!  Do not edit.",
        ""
    ]
    for c in cookies_dict.values():
        lines.append(f"{c['domain']}\t{c['flag']}\t{c['path']}\t{c['secure']}\t{c['expiration']}\t{c['name']}\t{c['value']}")
    return "\n".join(lines)


@app.route("/api/cookies/upload", methods=["POST"])
def upload_cookies():
    client_id = request.form.get("client_id")
    if not client_id:
        return jsonify({"status": "error", "message": "Client ID is required."}), 400
        
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded."}), 400
        
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "No selected file."}), 400
        
    try:
        content = file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to read file content: {e}"}), 400

    new_cookies = parse_cookies_to_dict(content)
    if not new_cookies:
        return jsonify({"status": "error", "message": "File cookie tải lên không hợp lệ hoặc không chứa cookie hợp lệ."}), 400

    cookies_dir = os.path.join(TEMP_DOWNLOAD_DIR, "cookies")
    os.makedirs(cookies_dir, exist_ok=True)
    
    filepath = os.path.join(cookies_dir, f"cookies_{client_id}.txt")
    
    # Read existing cookies if file exists, then merge
    merged_cookies = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                existing_content = f.read()
            merged_cookies = parse_cookies_to_dict(existing_content)
        except Exception as e:
            logger.warning(f"Could not read existing cookies file for merging: {e}")
            
    # Merge new cookies (new overrides existing on conflict)
    merged_cookies.update(new_cookies)
    
    merged_content = serialize_netscape_cookies(merged_cookies)
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(merged_content)
    except Exception as e:
         return jsonify({"status": "error", "message": f"Failed to save cookies to server: {e}"}), 500
         
    logger.info(f"Saved merged cookies for client {client_id}")
    return jsonify({"status": "success", "message": "Cookies uploaded and merged successfully!"})


@app.route("/api/cookies/status/<client_id>", methods=["GET"])
def get_cookie_status(client_id):
    if not client_id:
        return jsonify({"has_cookies": False})
        
    client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")
    if not os.path.exists(client_cookies):
        return jsonify({"has_cookies": False})
        
    domains = set()
    try:
        with open(client_cookies, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        parsed = parse_cookies_to_dict(content)
        for key in parsed.keys():
            domain = key[0]
            if "facebook.com" in domain or "fb.com" in domain:
                domains.add("Facebook")
            elif "instagram.com" in domain:
                domains.add("Instagram")
            elif "youtube.com" in domain or "youtu.be" in domain:
                domains.add("YouTube")
            elif "tiktok.com" in domain:
                domains.add("TikTok")
            elif "threads.net" in domain or "threads.com" in domain:
                domains.add("Threads")
    except Exception as e:
        logger.warning(f"Error parsing cookies for status check: {e}")
        
    return jsonify({
        "has_cookies": True,
        "domains": sorted(list(domains))
    })


@app.route("/api/cookies/clear/<client_id>", methods=["POST"])
def clear_cookies(client_id):
    if not client_id:
        return jsonify({"status": "error", "message": "Client ID is required."}), 400
        
    client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")
    if os.path.exists(client_cookies):
        try:
            os.remove(client_cookies)
            logger.info(f"Cleared cookies for client {client_id}")
            return jsonify({"status": "success", "message": "Cookies cleared successfully."})
        except Exception as e:
            return jsonify({"status": "error", "message": f"Failed to clear cookies: {e}"}), 500
            
    return jsonify({"status": "success", "message": "No cookies to clear."})


def format_duration(seconds):
    """Convert seconds to human-readable duration string."""
    if not seconds:
        return "Unknown"
    seconds = int(seconds)
    mins = seconds // 60
    secs = seconds % 60
    hours = mins // 60
    mins = mins % 60
    if hours > 0:
        return f"{hours:d}:{mins:02d}:{secs:02d}"
    return f"{mins:d}:{secs:02d}"


def format_size(size_bytes):
    """Convert bytes to human-readable size string."""
    if not size_bytes:
        return None
    size_bytes = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def get_url_content_length(url, cookies_file=None):
    """Fetches the Content-Length of a URL via HTTP HEAD request."""
    import requests
    import os
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }
    
    req_headers = headers.copy()
    if "tiktok" in url.lower() or "tiktokcdn" in url.lower():
        req_headers["Referer"] = "https://www.tiktok.com/"

    use_session = False
    if cookies_file and os.path.exists(cookies_file):
        try:
            import http.cookiejar
            cookie_jar = http.cookiejar.MozillaCookieJar()
            cookie_jar.load(cookies_file, ignore_discard=True, ignore_expires=True)
            session = requests.Session()
            session.cookies.update(cookie_jar)
            use_session = True
        except Exception:
            pass

    try:
        if use_session:
            response = session.head(url, headers=req_headers, timeout=3, allow_redirects=True)
            if response.status_code not in [200, 206]:
                response = session.get(url, headers=req_headers, stream=True, timeout=3, allow_redirects=True)
        else:
            response = requests.head(url, headers=req_headers, timeout=3, allow_redirects=True)
            if response.status_code not in [200, 206]:
                response = requests.get(url, headers=req_headers, stream=True, timeout=3, allow_redirects=True)
            
        if response.status_code in [200, 206]:
            length = response.headers.get('content-length')
            if length:
                return int(length)
                
            # If chunked transfer-encoding or content-length is missing
            total_bytes = 0
            for chunk in response.iter_content(chunk_size=8192):
                total_bytes += len(chunk)
                if total_bytes > 5 * 1024 * 1024:  # limit to 5MB
                    break
            if total_bytes > 0:
                return total_bytes
    except Exception:
        pass
    return None


def extract_instagram_via_gallery_dl(url, client_id):
    """
    Invokes gallery-dl via subprocess to extract Instagram photo/video posts.
    Reuses the client's uploaded J2TEAM cookies if available.
    """
    import subprocess
    import json
    import os
    
    # Locate gallery-dl executable
    gallery_dl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "Scripts", "gallery-dl.exe")
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
                from datetime import datetime
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
        from concurrent.futures import ThreadPoolExecutor
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


def extract_tiktok_slideshow_via_gallery_dl(url, client_id):
    """
    Invokes gallery-dl via subprocess to extract TikTok slideshows.
    Reuses the client's uploaded cookies if available.
    """
    import subprocess
    import json
    import os
    
    gallery_dl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "Scripts", "gallery-dl.exe")
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
                from datetime import datetime
                dt = datetime.fromtimestamp(int(create_time))
                upload_date = dt.strftime("%d %b %Y")
            except Exception:
                pass
        # Resolve sizes of photo options in parallel without cookies (to avoid 30s delays on CDN links)
        from concurrent.futures import ThreadPoolExecutor
        
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



def scrape_fb_post(url, client_id=None):
    import requests
    import json
    import re
    import urllib.parse
    import html as html_lib

    session = requests.Session()
    headers = {
        "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_patched.html)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    # Try using client cookies if available
    cookies_dir = os.path.join(TEMP_DOWNLOAD_DIR, "cookies")
    cookie_file = os.path.join(cookies_dir, f"cookies_{client_id}.txt") if client_id else None
    if cookie_file and os.path.exists(cookie_file):
        import http.cookiejar
        cookie_jar = http.cookiejar.MozillaCookieJar()
        try:
            cookie_jar.load(cookie_file, ignore_discard=True, ignore_expires=True)
            session.cookies.update(cookie_jar)
            logger.info(f"Loaded client cookies for custom Facebook scraping.")
        except Exception as e:
            logger.warning(f"Error loading cookies for custom Facebook scraping: {e}")
            
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
        title = html_lib.unescape(title)
        
    title_match = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html)
    uploader = "Facebook User"
    if title_match:
        full_title = html_lib.unescape(title_match.group(1))
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
    added_image_urls = set()
    
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
                                    if uri not in added_image_urls:
                                        added_image_urls.add(uri)
                                        images.append({
                                            "label": f"Photo {len(images)+1}",
                                            "url": uri,
                                            "ext": "jpg"
                                        })
            
            # Check for direct Photo types
            if d.get("__typename") == "Photo" or "viewer_image" in d:
                v_img = d.get("viewer_image")
                if isinstance(v_img, dict) and v_img.get("uri"):
                    uri = v_img["uri"].replace("\\/", "/").replace("\\u0025", "%")
                    uri = urllib.parse.unquote(uri)
                    if uri not in added_image_urls:
                        added_image_urls.add(uri)
                        images.append({
                            "label": f"Photo {len(images)+1}",
                            "url": uri,
                            "ext": "jpg"
                        })
                else:
                    img = d.get("image")
                    if isinstance(img, dict) and img.get("uri"):
                        uri = img["uri"].replace("\\/", "/").replace("\\u0025", "%")
                        uri = urllib.parse.unquote(uri)
                        if uri not in added_image_urls:
                            added_image_urls.add(uri)
                            images.append({
                                "label": f"Photo {len(images)+1}",
                                "url": uri,
                                "ext": "jpg"
                            })
                            
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
        images.append({
            "label": "Thumbnail",
            "url": thumbnail,
            "ext": "jpg"
        })
        
    # Map photos to video_options if no video exists
    if not video_options and images:
        for idx, img_obj in enumerate(images):
            video_options.append({
                "format_id": f"direct_photo_{idx+1}",
                "ext": "jpg",
                "resolution": "Original",
                "size": "Unknown Size",
                "label": f"Photo Option {idx+1}",
                "url": img_obj["url"]
            })

    return {
        "status": "success",
        "title": title,
        "duration": "0:05" if not video_options or any("photo" in o["format_id"] for o in video_options) else "0:30",
        "uploader": uploader,
        "thumbnail": thumbnail or (images[0]["url"] if images else ""),
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


def extract_shortcode(url):
    import re
    # Match shortcode from threads URL
    # https://www.threads.net/@username/post/SHORTCODE
    # or https://threads.com/@username/post/SHORTCODE
    # or https://www.threads.net/t/SHORTCODE
    # or https://threads.com/t/SHORTCODE
    match = re.search(r'/post/([^/?#\s]+)', url)
    if not match:
        match = re.search(r'/t/([^/?#\s]+)', url)
    return match.group(1) if match else None

def parse_threads_page(url, client_id=None):
    import requests
    import json
    import re
    import http.cookiejar
    
    shortcode = extract_shortcode(url)
    if not shortcode:
        return {"status": "error", "message": "Không thể trích xuất shortcode từ URL Threads."}
        
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
        cookies_dir = os.path.join(TEMP_DOWNLOAD_DIR, "cookies")
        cookie_file = os.path.join(cookies_dir, f"cookies_{client_id}.txt") if client_id else None
        
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
                "message": "Threads yêu cầu xác minh danh tính hoặc đây là bài viết riêng tư. Vui lòng xuất và tải lên file cookie J2TEAM (chọn định dạng Netscape hoặc JSON) của Instagram/Threads để tiếp tục."
            }
        return {"status": "error", "message": "Không thể trích xuất thông tin bài viết từ trang Threads này. Có thể bài viết đã bị xóa hoặc giới hạn truy cập."}
        
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
            "message": "Bài viết Threads này chỉ chứa văn bản và không có hình ảnh hoặc video để tải xuống."
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
            
    # Resolve sizes of video_options in parallel using ThreadPoolExecutor
    from concurrent.futures import ThreadPoolExecutor
    client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt") if client_id else None
    
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
        "upload_date": "Hôm nay",
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


@app.route("/api/info", methods=["POST"])
def get_info():
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    if "tiktok.com" in url.lower() and "/photo/" in url.lower():
        import re
        url = re.sub(r'/photo/', '/video/', url, flags=re.IGNORECASE)
    client_id = data.get("client_id")

    if not url:
        return jsonify({"status": "error", "message": "Link URL is required."}), 400

    is_threads = "threads.net" in url.lower() or "threads.com" in url.lower()
    if is_threads:
        try:
            threads_info = parse_threads_page(url, client_id)
            if threads_info.get("status") == "success":
                return jsonify(threads_info)
            else:
                return jsonify(threads_info), 400
        except Exception as e:
            logger.error(f"Failed to scrape Threads: {e}")
            return jsonify({
                "status": "error",
                "message": f"Failed to extract Threads contents: {e}"
            }), 500


    is_instagram = "instagram.com" in url.lower() or "instagr.am" in url.lower()
    if is_instagram:
        lower_url = url.lower()
        if not any(path in lower_url for path in ["/p/", "/reel/", "/reels/", "/stories/", "/tv/"]):
            return jsonify({
                "status": "error",
                "message": "Vui lòng nhập liên kết của một bài đăng (Post), Reel, Story hoặc TV cụ thể trên Instagram thay vì trang cá nhân của người dùng."
            }), 400

    if "/stories/" in url and ("facebook.com" in url or "fb.com" in url or "fb.watch" in url):
        client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt") if client_id else None
        if not client_cookies or not os.path.exists(client_cookies):
            return jsonify({
                "status": "error",
                "message": "Cookies are required to download Facebook Stories. Please export and upload your cookies first."
            }), 400
            
        try:
            import subprocess
            import re
            import urllib.parse
            
            command = [
                "curl",
                "-s",
                "-L",
                "-b", client_cookies,
                "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "-H", "Accept-Language: vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "-H", "Sec-Fetch-Mode: navigate",
                "-H", "Upgrade-Insecure-Requests: 1",
                url
            ]
            
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
            html = result.stdout
            
            if "Sorry, something went wrong" in html or len(html) < 20000:
                if "login.php" in html or "login_form" in html:
                    return jsonify({
                        "status": "error",
                        "message": "Unable to authenticate with Facebook. Your uploaded cookies may be expired or invalid. Please re-export and upload them."
                    }), 400
                return jsonify({
                    "status": "error",
                    "message": "Facebook returned an error or blocked the request. Please check if your cookies file is valid and active."
                }), 400

            uploader = "Facebook User"
            owner_match = re.search(r'"story_bucket_owner"\s*:\s*{[^}]+?"name"\s*:\s*"([^"]+)"', html)
            if owner_match:
                uploader = owner_match.group(1)
            else:
                owner_match2 = re.search(r'"owner"\s*:\s*{\s*"name"\s*:\s*"([^"]+)"', html)
                if owner_match2:
                    uploader = owner_match2.group(1)

            title = f"Story by {uploader}" if uploader != "Facebook User" else "Facebook Story"

            bucket_id = None
            story_id = None
            url_match = re.search(r'/stories/([^/]+)/([^//?]+)', url)
            if url_match:
                bucket_id = url_match.group(1)
                story_id = url_match.group(2)
            else:
                url_match2 = re.search(r'/stories/([^//?]+)', url)
                if url_match2:
                    bucket_id = url_match2.group(1)

            # Try JSON extraction first
            parsed_stories = []
            uploader_from_json = None
            import json
            scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
            
            def search_for_buckets(d):
                nonlocal uploader_from_json
                if isinstance(d, dict):
                    for k in ['unified_stories', 'unified_stories_with_notes']:
                        if k in d and isinstance(d[k], dict) and 'edges' in d[k]:
                            edges = d[k]['edges']
                            if edges:
                                current_bucket_id = d.get('id')
                                if bucket_id and str(current_bucket_id) != str(bucket_id):
                                    continue
                                    
                                owner = d.get('story_bucket_owner') or d.get('owner')
                                if isinstance(owner, dict) and owner.get('name'):
                                    uploader_from_json = owner.get('name')
                                    
                                for edge in edges:
                                    node = edge.get('node') if isinstance(edge, dict) else None
                                    if not isinstance(node, dict):
                                        continue
                                    card_id = node.get('id')
                                    if any(s['card_id'] == card_id for s in parsed_stories):
                                        continue
                                        
                                    attachments = node.get('attachments') or []
                                    media = None
                                    if attachments and isinstance(attachments, list):
                                        att = attachments[0]
                                        if isinstance(att, dict):
                                            media = att.get('media')
                                    if not media and 'media' in node:
                                        media = node.get('media')
                                        
                                    if isinstance(media, dict):
                                        typename = media.get('__typename')
                                        media_id = media.get('id')
                                        playable_url = media.get('playable_url') or media.get('progressive_url')
                                        if playable_url:
                                            playable_url = playable_url.replace("\\/", "/").replace("\\u0025", "%")
                                            playable_url = urllib.parse.unquote(playable_url)
                                            
                                        thumbnail_uri = None
                                        preferred_thumbnail = media.get('preferred_thumbnail')
                                        if isinstance(preferred_thumbnail, dict):
                                            img = preferred_thumbnail.get('image')
                                            if isinstance(img, dict) and img.get('uri'):
                                                thumbnail_uri = img.get('uri')
                                        if not thumbnail_uri:
                                            img_node = media.get('image') or media.get('previewImage')
                                            if isinstance(img_node, dict) and img_node.get('uri'):
                                                thumbnail_uri = img_node.get('uri')
                                        
                                        if thumbnail_uri:
                                            thumbnail_uri = thumbnail_uri.replace("\\/", "/").replace("\\u0025", "%")
                                            thumbnail_uri = urllib.parse.unquote(thumbnail_uri)
                                            
                                        parsed_stories.append({
                                            'card_id': card_id,
                                            'typename': typename,
                                            'media_id': media_id,
                                            'playable_url': playable_url,
                                            'thumbnail_uri': thumbnail_uri
                                        })
                    for v in d.values():
                        search_for_buckets(v)
                elif isinstance(d, list):
                    for item in d:
                        search_for_buckets(item)

            for script in scripts:
                try:
                    data = json.loads(script)
                    search_for_buckets(data)
                except Exception:
                    pass

            video_options = []
            unique_video_urls = []
            unique_photo_urls = []
            if parsed_stories:
                if uploader_from_json:
                    uploader = uploader_from_json
                    title = f"Story by {uploader}"
                    
                # Prioritize active story at the top
                active_story_idx = -1
                for idx, s in enumerate(parsed_stories):
                    if story_id and s['card_id'] == story_id:
                        active_story_idx = idx
                        break
                if active_story_idx != -1:
                    active_story = parsed_stories.pop(active_story_idx)
                    parsed_stories.insert(0, active_story)
                    
                video_count = 0
                photo_count = 0
                for idx, s in enumerate(parsed_stories):
                    is_active = (story_id and s['card_id'] == story_id) or (idx == 0 and not story_id)
                    
                    if s['playable_url']:
                        video_count += 1
                        label = f"Video Story {video_count} (Current)" if is_active else f"Video Story {video_count}"
                        video_options.append({
                            "format_id": f"direct_video_{idx+1}",
                            "ext": "mp4",
                            "resolution": "HD" if "quality_hd" in s['playable_url'].lower() else "SD",
                            "size": "Unknown Size",
                            "label": label,
                            "url": s['playable_url']
                        })
                        unique_video_urls.append(s['playable_url'])
                    
                    if s['thumbnail_uri']:
                        unique_photo_urls.append(s['thumbnail_uri'])
                        if not s['playable_url']:
                            photo_count += 1
                            label = f"Photo Story {photo_count} (Current)" if is_active else f"Photo Story {photo_count}"
                            video_options.append({
                                "format_id": f"direct_photo_{idx+1}",
                                "ext": "jpg",
                                "resolution": "Original",
                                "size": "Unknown Size",
                                "label": label,
                                "url": s['thumbnail_uri']
                            })

            if not video_options:
                # Fallback to regex extraction
                raw_playable = re.findall(r'"playable_url"\s*:\s*"([^"]+)"', html)
                raw_progressive = re.findall(r'"progressive_url"\s*:\s*"([^"]+)"', html)
                
                unique_video_urls = []
                for u in raw_playable + raw_progressive:
                    clean = u.replace("\\/", "/").replace("\\u0025", "%")
                    clean = urllib.parse.unquote(clean)
                    if clean not in unique_video_urls and "fbcdn.net" in clean:
                        if "dash_baseline" in clean or "_nc_vs" in clean or "dash_prefetch" in clean:
                            continue
                        unique_video_urls.append(clean)
                        
                raw_photos = re.findall(r'"preferred_thumbnail"\s*:\s*{\s*"image"\s*:\s*{\s*"uri"\s*:\s*"([^"]+)"', html)
                raw_photos2 = re.findall(r'"overlay_image_uri"\s*:\s*"([^"]+)"', html)
                
                unique_photo_urls = []
                for u in raw_photos + raw_photos2:
                    clean = u.replace("\\/", "/").replace("\\u0025", "%")
                    clean = urllib.parse.unquote(clean)
                    if clean not in unique_photo_urls and "fbcdn.net" in clean:
                        unique_photo_urls.append(clean)

                active_video_url = None
                active_photo_url = None
                if story_id:
                    pos = html.find(story_id)
                    if pos != -1:
                        segment = html[pos:pos+150000]
                        media_match = re.search(r'"media"\s*:\s*{\s*"id"\s*:\s*"(\d+)"', segment)
                        if media_match:
                            media_id = media_match.group(1)
                            video_pos = html.find(f'"video_id":"{media_id}"')
                            if video_pos != -1:
                                video_segment = html[max(0, video_pos-3000):video_pos+1000]
                                url_match = re.search(r'"playable_url"\s*:\s*"([^"]+)"', video_segment) or re.search(r'"progressive_url"\s*:\s*"([^"]+)"', video_segment)
                                if url_match:
                                    active_video_url = url_match.group(1).replace("\\/", "/").replace("\\u0025", "%")
                                    active_video_url = urllib.parse.unquote(active_video_url)
                            else:
                                photo_pos = html.find(media_id)
                                if photo_pos != -1:
                                    photo_segment = html[photo_pos:photo_pos+5000]
                                    url_match = re.search(r'"uri"\s*:\s*"([^"]+)"', photo_segment)
                                    if url_match:
                                        active_photo_url = url_match.group(1).replace("\\/", "/").replace("\\u0025", "%")
                                        active_photo_url = urllib.parse.unquote(active_photo_url)

                if active_video_url and active_video_url in unique_video_urls:
                    unique_video_urls.remove(active_video_url)
                    unique_video_urls.insert(0, active_video_url)
                if active_photo_url and active_photo_url in unique_photo_urls:
                    unique_photo_urls.remove(active_photo_url)
                    unique_photo_urls.insert(0, active_photo_url)

                for idx, v_url in enumerate(unique_video_urls):
                    is_active = (v_url == active_video_url) or (idx == 0 and not active_video_url)
                    label = f"Video Story {idx+1} (Current)" if is_active else f"Video Story {idx+1}"
                    video_options.append({
                        "format_id": f"direct_video_{idx+1}",
                        "ext": "mp4",
                        "resolution": "HD" if "quality_hd" in v_url.lower() else "SD",
                        "size": "Unknown Size",
                        "label": label,
                        "url": v_url
                    })
                    
                for idx, p_url in enumerate(unique_photo_urls):
                    is_active = (p_url == active_photo_url) or (idx == 0 and not active_photo_url and not unique_video_urls)
                    label = f"Photo Story {idx+1} (Current)" if is_active else f"Photo Story {idx+1}"
                    video_options.append({
                        "format_id": f"direct_photo_{idx+1}",
                        "ext": "jpg",
                        "resolution": "Original",
                        "size": "Unknown Size",
                        "label": label,
                        "url": p_url
                    })

            if not video_options:
                return jsonify({
                    "status": "error",
                    "message": "Could not find any video or photo resources in the Story. The story may have expired or been deleted."
                }), 400

            thumbnail = unique_photo_urls[0] if unique_photo_urls else "https://www.facebook.com/images/assets_files/yoodle/yoodle_default.png"
            
            images = []
            for idx, p_url in enumerate(unique_photo_urls):
                images.append({
                    "label": f"Story Thumbnail {idx+1}",
                    "url": p_url,
                    "ext": "jpg"
                })

            # Resolve sizes of video_options in parallel using ThreadPoolExecutor
            from concurrent.futures import ThreadPoolExecutor
            client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt") if client_id else None
            
            def resolve_fb_story_size(opt):
                url_to_check = opt.get("url")
                if url_to_check:
                    s_bytes = get_url_content_length(url_to_check, cookies_file=client_cookies)
                    if s_bytes:
                        opt["size"] = format_size(s_bytes)

            if video_options:
                with ThreadPoolExecutor(max_workers=min(10, len(video_options))) as executor:
                    list(executor.map(resolve_fb_story_size, video_options))

            result = {
                "status": "success",
                "title": title,
                "duration": "0:15" if unique_video_urls else "0:05",
                "uploader": uploader,
                "thumbnail": thumbnail,
                "views": "N/A",
                "likes": "N/A",
                "upload_date": "Today",
                "category": "Facebook Story",
                "tags": ["Story"],
                "subtitles": [],
                "video_options": video_options,
                "audio_options": [],
                "images": images,
                "platform": "Facebook Story",
                "platform_class": "facebook-story"
            }
            logger.info(f"Successfully extracted {len(video_options)} Facebook Story options.")
            return jsonify(result)

        except Exception as e:
            logger.error(f"Error scraping Facebook Story: {e}")
            return jsonify({
                "status": "error",
                "message": f"Failed to extract Facebook Story contents: {e}"
            }), 500

    logger.info(f"Fetching metadata for URL: {url} (client_id: {client_id})")

    is_facebook = any(domain in url.lower() for domain in ["facebook.com", "fb.com", "fb.watch", "fb.gg"])
    is_fb_story = "/stories/" in url.lower()
    
    if is_facebook and not is_fb_story:
        try:
            logger.info(f"Facebook Post URL detected. Attempting custom scraping via facebookexternalhit: {url}")
            fb_info = scrape_fb_post(url, client_id)
            if fb_info and fb_info.get("status") == "success" and (fb_info.get("images") or fb_info.get("video_options")):
                # Resolve sizes of video_options in parallel using ThreadPoolExecutor
                video_options = fb_info.get("video_options", [])
                if video_options:
                    from concurrent.futures import ThreadPoolExecutor
                    client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt") if client_id else None
                    
                    def resolve_fb_post_size(opt):
                        url_to_check = opt.get("url")
                        if url_to_check:
                            s_bytes = get_url_content_length(url_to_check, cookies_file=client_cookies)
                            if s_bytes:
                                opt["size"] = format_size(s_bytes)
                                
                    with ThreadPoolExecutor(max_workers=min(10, len(video_options))) as executor:
                        list(executor.map(resolve_fb_post_size, video_options))
                        
                logger.info(f"Successfully scraped Facebook post using custom scraper. Options: {len(video_options)}")
                return jsonify(fb_info)
            else:
                logger.warning("Custom Facebook post scraping returned no content. Falling back to yt-dlp...")
        except Exception as fb_scrape_err:
            logger.warning(f"Custom Facebook post scraping failed: {fb_scrape_err}. Falling back to yt-dlp...")

    original_url = data.get("url", "").strip()
    is_tiktok_photo = "tiktok.com" in original_url.lower() and "/photo/" in original_url.lower()
    if is_tiktok_photo:
        try:
            logger.info("TikTok Photo post detected. Attempting extraction via gallery-dl first...")
            gallery_info = extract_tiktok_slideshow_via_gallery_dl(url, client_id)
            if gallery_info:
                logger.info("Successfully extracted TikTok Slideshow using gallery-dl.")
                return jsonify(gallery_info)
        except Exception as gallery_e:
            logger.warning(f"Primary gallery-dl TikTok extraction failed: {gallery_e}. Falling back to yt-dlp...")
            if any(keyword in str(gallery_e).lower() for keyword in ["login", "redirect", "cookie", "captcha"]):
                return jsonify({
                    "status": "error",
                    "message": "Video hoặc Slideshow TikTok này yêu cầu cookie tài khoản để truy cập hoặc IP hệ thống đang bị chặn (gặp captcha). Vui lòng đăng nhập vào TikTok trên trình duyệt, xuất và tải lên file cookie J2TEAM (chọn định dạng Netscape hoặc JSON) của TikTok để tiếp tục."
                }), 400

    is_instagram = "instagram.com" in url.lower() or "instagr.am" in url.lower()

    if is_instagram:
        try:
            logger.info("Instagram URL detected. Attempting extraction via gallery-dl first...")
            gallery_info = extract_instagram_via_gallery_dl(url, client_id)
            if gallery_info:
                logger.info("Successfully extracted Instagram metadata using gallery-dl.")
                return jsonify(gallery_info)
        except Exception as gallery_e:
            logger.warning(f"Primary gallery-dl extraction failed: {gallery_e}. Falling back to yt-dlp...")
            if any(keyword in str(gallery_e).lower() for keyword in ["login", "redirect", "cookie"]):
                return jsonify({
                    "status": "error",
                    "message": "Instagram yêu cầu cookie tài khoản để truy cập. Vui lòng xuất và tải lên file cookie J2TEAM (chọn định dạng Netscape hoặc JSON) để tiếp tục."
                }), 400

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "noplaylist": not is_instagram,
        "js_runtimes": {"deno": {}, "node": {}, "bun": {}, "quickjs": {}},
        "cookiesfrombrowser": "auto",
        "ignoreerrors": False,
    }

    try:
        info = None
        first_err = None
        try:
            with create_ydl_instance(ydl_opts, url, client_id) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            first_err = e
            logger.warning(f"Metadata extraction with cookies failed: {e}. Retrying without cookies...")

        if not info:
            logger.info("Retrying metadata extraction without cookies...")
            ydl_opts_nocookies = ydl_opts.copy()
            ydl_opts_nocookies.pop("cookiefile", None)
            ydl_opts_nocookies.pop("cookiesfrombrowser", None)
            try:
                with yt_dlp.YoutubeDL(ydl_opts_nocookies) as ydl_nocookies:
                    info = ydl_nocookies.extract_info(url, download=False)
            except Exception as nocookie_e:
                logger.error(f"Metadata extraction without cookies also failed: {nocookie_e}")
                err_str = f"{str(first_err)} | {str(nocookie_e)}".lower()
                
                is_facebook = any(domain in url.lower() for domain in ["facebook.com", "fb.com", "fb.watch", "fb.gg"])
                if is_facebook:
                    fb_auth_keywords = [
                        "registered users",
                        "log in",
                        "login",
                        "sign in",
                        "private",
                        "permission",
                        "cookies",
                        "cookies-from-browser"
                    ]
                    if any(keyword in err_str for keyword in fb_auth_keywords):
                        return jsonify({
                            "status": "error",
                            "message": "Facebook yêu cầu cookie tài khoản để truy cập bài viết/video này (có thể là video riêng tư, giới hạn đối tượng hoặc trong nhóm kín). Vui lòng đăng nhập vào Facebook trên trình duyệt, xuất và tải lên file cookie J2TEAM (chọn định dạng Netscape hoặc JSON) của Facebook để tiếp tục."
                        }), 400

                is_youtube = any(domain in url.lower() for domain in ["youtube.com", "youtu.be", "youtubekids.com", "youtube-nocookie.com"])
                if is_youtube:
                    youtube_auth_keywords = [
                        "confirm you're not a bot", 
                        "confirm you are not a bot",
                        "sign in to confirm", 
                        "sign in to view",
                        "sign in", 
                        "confirm your age", 
                        "private video", 
                        "this video is private",
                        "use --cookies",
                        "cookies-from-browser"
                    ]
                    if any(keyword in err_str for keyword in youtube_auth_keywords):
                        return jsonify({
                            "status": "error",
                            "message": "YouTube yêu cầu xác minh danh tính (Sign in / Confirm you are not a bot) hoặc video này là riêng tư/giới hạn độ tuổi. Vui lòng xuất và tải lên file cookie J2TEAM (chọn định dạng Netscape hoặc JSON) của YouTube để tiếp tục."
                        }), 400

                is_tiktok = "tiktok" in url.lower()
                if is_tiktok:
                    tiktok_auth_keywords = [
                        "confirm you're not a bot",
                        "confirm you are not a bot",
                        "captcha",
                        "block",
                        "log in",
                        "login",
                        "sign in",
                        "private",
                        "permission",
                        "cookies",
                        "cookies-from-browser",
                        "not available",
                        "unexpected response",
                        "unable to extract",
                        "rehydration"
                    ]
                    if any(keyword in err_str for keyword in tiktok_auth_keywords):
                        return jsonify({
                            "status": "error",
                            "message": "Video hoặc Slideshow TikTok này yêu cầu cookie tài khoản để truy cập hoặc IP hệ thống đang bị chặn (gặp captcha). Vui lòng đăng nhập vào TikTok trên trình duyệt, xuất và tải lên file cookie J2TEAM (chọn định dạng Netscape hoặc JSON) của TikTok để tiếp tục."
                        }), 400

                # --- Instagram photo post fallback ---
                if is_instagram:

                    try:
                        gallery_info = extract_instagram_via_gallery_dl(url, client_id)
                        if gallery_info:
                            return jsonify(gallery_info)
                    except Exception as gallery_e:
                        if any(keyword in str(gallery_e).lower() for keyword in ["login", "redirect", "cookie"]):
                            return jsonify({
                                "status": "error",
                                "message": "Instagram yêu cầu cookie tài khoản để truy cập. Vui lòng xuất và tải lên file cookie J2TEAM (chọn định dạng Netscape hoặc JSON) để tiếp tục."
                            }), 400

                if "there is no video in this post" in err_str:
                    return jsonify({
                        "status": "error",
                        "message": "Không thể tải được thông tin hình ảnh từ Instagram. Instagram có thể yêu cầu cookie tài khoản để truy cập bài viết này. Vui lòng tải lên cookie J2TEAM (chọn định dạng Netscape hoặc JSON) để tiếp tục."
                    }), 400
                if is_instagram and any(keyword in err_str for keyword in ["login", "logged-in", "cookies", "redirect", "confirm your age", "challenge", "checkpoint", "sign in", "rate limit", "empty media", "unable to extract"]):
                    return jsonify({
                        "status": "error",
                        "message": "Instagram yêu cầu cookie tài khoản để truy cập. Vui lòng xuất và tải lên file cookie J2TEAM (chọn định dạng Netscape hoặc JSON) để tiếp tục."
                    }), 400
                return jsonify({
                    "status": "error",
                    "message": f"Unable to extract media metadata: {nocookie_e}"
                }), 400

        if not info:
            if is_instagram:
                # --- Instagram photo post fallback ---
                try:
                    gallery_info = extract_instagram_via_gallery_dl(url, client_id)
                    if gallery_info:
                        return jsonify(gallery_info)
                except Exception as gallery_e:
                    if any(keyword in str(gallery_e).lower() for keyword in ["login", "redirect", "cookie"]):
                        return jsonify({
                            "status": "error",
                            "message": "Instagram yêu cầu cookie tài khoản để truy cập. Vui lòng xuất và tải lên file cookie J2TEAM (chọn định dạng Netscape hoặc JSON) để tiếp tục."
                        }), 400
                return jsonify({
                    "status": "error",
                    "message": "Instagram yêu cầu cookie tài khoản để truy cập. Vui lòng xuất và tải lên file cookie J2TEAM (chọn định dạng Netscape hoặc JSON) để tiếp tục."
                }), 400
            return jsonify({
                "status": "error",
                "message": "Failed to extract media metadata."
            }), 400

        if True:
            if is_instagram and info:
                formats_list = info.get("formats", [])
                entries = info.get("entries", [])
                has_video = False
                if formats_list:
                    has_video = any(f.get("vcodec") != "none" for f in formats_list)
                elif entries:
                    has_video = True
                    
                if not has_video:
                    logger.info("Instagram post has no video formats/entries. Falling back to gallery-dl.")
                    try:
                        gallery_info = extract_instagram_via_gallery_dl(url, client_id)
                        if gallery_info:
                            return jsonify(gallery_info)
                    except Exception as gallery_e:
                        logger.warning(f"gallery-dl fallback failed for photo post: {gallery_e}")
                        if any(keyword in str(gallery_e).lower() for keyword in ["login", "redirect", "cookie"]):
                            return jsonify({
                                "status": "error",
                                "message": "Instagram yêu cầu cookie tài khoản để truy cập. Vui lòng xuất và tải lên file cookie J2TEAM (chọn định dạng Netscape hoặc JSON) để tiếp tục."
                            }), 400

            if info:
                extractor = info.get("extractor", "").lower() or info.get("extractor_key", "").lower() or ""
                is_tiktok = "tiktok" in extractor or "tiktok" in url.lower()
                if is_tiktok:
                    formats_list = info.get("formats", [])
                    has_video = False
                    if formats_list:
                        has_video = any(f.get("vcodec") != "none" for f in formats_list)
                    if not has_video:
                        logger.info("TikTok post has no video formats (detected slideshow). Falling back to gallery-dl.")
                        try:
                            slideshow_info = extract_tiktok_slideshow_via_gallery_dl(url, client_id)
                            if slideshow_info:
                                return jsonify(slideshow_info)
                        except Exception as gallery_e:
                            logger.warning(f"TikTok gallery-dl fallback failed for slideshow post: {gallery_e}")
                            if any(keyword in str(gallery_e).lower() for keyword in ["login", "redirect", "cookie", "captcha"]):
                                return jsonify({
                                    "status": "error",
                                    "message": "Video hoặc Slideshow TikTok này yêu cầu cookie tài khoản để truy cập hoặc IP hệ thống đang bị chặn (gặp captcha). Vui lòng đăng nhập vào TikTok trên trình duyệt, xuất và tải lên file cookie J2TEAM (chọn định dạng Netscape hoặc JSON) của TikTok để tiếp tục."
                                }), 400

            extractor = info.get("extractor_key", "").lower() if info.get("extractor_key") else ""

            title = info.get("title", "Unknown Title")
            duration_sec = info.get("duration", 0)
            duration = format_duration(duration_sec)
            uploader = info.get("uploader", "Unknown Channel")
            thumbnail = info.get("thumbnail") or (
                info.get("thumbnails")[-1].get("url") if info.get("thumbnails") else None
            )

            # --- Rich Metadata extraction ---
            view_count = info.get("view_count")
            like_count = info.get("like_count")
            
            def format_count(count):
                if not count:
                    return "0"
                count = int(count)
                if count >= 1_000_000:
                    return f"{count / 1_000_000:.1f}M"
                if count >= 1_000:
                    return f"{count / 1_000:.1f}K"
                return str(count)
                
            views_label = format_count(view_count) if view_count else ("N/A" if is_instagram else "Unknown")
            likes_label = format_count(like_count) if like_count else "Unknown"
            
            # Clean up Facebook title and extract views/reactions if present in the title
            if "facebook" in extractor:
                import re
                fb_match = re.match(r"^([\d.,]+[KMB]?) views?\s*·\s*([\d.,]+[KMB]?)\s*reactions?\s*\|\s*(.*)$", title, re.IGNORECASE)
                if fb_match:
                    views_label = fb_match.group(1)
                    likes_label = fb_match.group(2)
                    title = fb_match.group(3)
                else:
                    fb_match_views = re.match(r"^([\d.,]+[KMB]?) views?\s*\|\s*(.*)$", title, re.IGNORECASE)
                    if fb_match_views:
                        views_label = fb_match_views.group(1)
                        title = fb_match_views.group(2)
                
                if uploader and uploader != "Unknown Channel":
                    title = re.compile(rf"\s*\|\s*{re.escape(uploader)}\s*$", re.IGNORECASE).sub("", title)

                # Fallback curl scraper for Facebook Reel/Video likes and views if still Unknown or 0
                if likes_label == "Unknown" or likes_label == "0" or views_label == "Unknown" or views_label == "0":
                    video_id = info.get("id")
                    if video_id:
                        client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt") if client_id else None
                        if client_cookies and os.path.exists(client_cookies):
                            try:
                                import subprocess
                                curl_url = f"https://m.facebook.com/watch/?v={video_id}"
                                command = [
                                    "curl",
                                    "-s",
                                    "-L",
                                    "-b", client_cookies,
                                    "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                                    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                                    "-H", "Accept-Language: vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                                    curl_url
                                ]
                                res = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
                                curl_html = res.stdout
                                
                                # Search for "reaction_count":{"count":XXXX}
                                if likes_label == "Unknown" or likes_label == "0":
                                    react_match = re.search(r'"reaction_count"\s*:\s*{\s*"count"\s*:\s*(\d+)', curl_html)
                                    if react_match:
                                        likes_val = int(react_match.group(1))
                                        likes_label = format_count(likes_val)
                                        logger.info(f"Scraped Facebook likes count {likes_val} from Comet HTML")
                                    else:
                                        react_match2 = re.search(r'"i18n_reaction_count"\s*:\s*"([^"]+)"', curl_html)
                                        if react_match2:
                                            likes_label = react_match2.group(1).replace(",", ".")
                                            logger.info(f"Scraped Facebook likes label {likes_label} from Comet HTML")

                                # Search for "video_view_count":XXXX
                                if views_label == "Unknown" or views_label == "0":
                                    views_match = re.search(r'"video_view_count"\s*:\s*(\d+)', curl_html)
                                    if views_match:
                                        views_val = int(views_match.group(1))
                                        views_label = format_count(views_val)
                                        logger.info(f"Scraped Facebook views count {views_val} from Comet HTML")
                            except Exception as ex:
                                logger.warning(f"Failed to scrape Facebook likes/views count: {ex}")
            
            raw_date = info.get("upload_date")
            formatted_date = "Unknown"
            if raw_date and len(raw_date) == 8:
                try:
                    from datetime import datetime
                    formatted_date = datetime.strptime(raw_date, "%Y%m%d").strftime("%d %b %Y")
                except Exception:
                    pass
                    
            description = info.get("description") or "No description available."
            category = info.get("categories")[0] if info.get("categories") else None
            tags = info.get("tags")[:5] if info.get("tags") else []

            # --- Subtitles extraction ---
            subtitles = []
            
            # Estimate subtitle sizes if duration is available
            duration_sec = info.get("duration") or 0
            est_sub_size = None
            if duration_sec:
                try:
                    # Average VTT size is roughly 50 bytes per second of video duration
                    # plus a base header size of about 100 bytes.
                    est_bytes = int(float(duration_sec) * 50) + 100
                    # Clamp between 1KB and 250KB
                    est_bytes = max(1024, min(est_bytes, 250 * 1024))
                    est_sub_size = format_size(est_bytes)
                except Exception:
                    pass

            # Manual subtitles
            raw_subs = info.get("subtitles") or {}
            for lang, formats in raw_subs.items():
                if lang == "live_chat":
                    continue
                lang_name = formats[0].get("name") if (formats and formats[0].get("name")) else lang.upper()
                subtitles.append({
                    "lang_code": lang,
                    "name": lang_name,
                    "is_auto": False,
                    "url": formats[0].get("url") if formats else None,
                    "size": est_sub_size or "Unknown Size"
                })
            # Auto captions (limit to common ones)
            raw_auto = info.get("automatic_captions") or {}
            preferred_auto_langs = ["vi", "en", "ja", "ko"]
            for lang in preferred_auto_langs:
                if lang in raw_auto and lang not in raw_subs:
                    formats = raw_auto[lang]
                    lang_name = (formats[0].get("name") if formats else lang.upper()) + " (Auto)"
                    subtitles.append({
                        "lang_code": lang,
                        "name": lang_name,
                        "is_auto": True,
                        "url": formats[0].get("url") if formats else None,
                        "size": est_sub_size or "Unknown Size"
                    })

            # Resolve sizes of subtitles in parallel using ThreadPoolExecutor only if they couldn't be estimated
            subs_to_resolve = [sub for sub in subtitles if sub.get("size") == "Unknown Size" or not sub.get("size")]
            if subs_to_resolve:
                from concurrent.futures import ThreadPoolExecutor
                client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt") if client_id else None
                
                def resolve_sub_size(opt):
                    url_to_check = opt.get("url")
                    if url_to_check:
                        s_bytes = get_url_content_length(url_to_check, cookies_file=client_cookies)
                        if s_bytes:
                            opt["size"] = format_size(s_bytes)

                with ThreadPoolExecutor(max_workers=min(10, len(subs_to_resolve))) as executor:
                    list(executor.map(resolve_sub_size, subs_to_resolve))

            images = []
            formats_list = info.get("formats", [])
            is_shorts = "/shorts/" in url or (info.get("duration", 0) and info.get("duration", 0) <= 60)

            video_options = []
            audio_options = []

            # --- Check for Instagram Carousel/Playlist (Story list) ---
            entries = info.get("entries") or []
            if is_instagram and entries:
                uploader = info.get("uploader") or info.get("playlist_uploader") or uploader
                title = info.get("title") or info.get("playlist_title") or title

                is_story = "/stories/" in url.lower()
                unit_label = "Story" if is_story else "Slide"

                for idx, entry in enumerate(entries):
                    if not entry:
                        continue
                    slide_num = idx + 1
                    entry_duration = entry.get("duration")

                    # Determine if it's video
                    entry_formats = entry.get("formats", [])
                    is_video_slide = False
                    if entry_formats:
                        is_video_slide = any(f.get("vcodec") != "none" for f in entry_formats)
                    elif entry.get("ext") in ["mp4", "mkv", "webm", "avi", "mov"]:
                        is_video_slide = True
                    elif entry.get("width") and entry.get("height") and not entry_formats:
                        is_video_slide = bool(entry_duration)

                    # Get direct URL
                    direct_url = None
                    if is_video_slide:
                        best_f = None
                        for f in entry_formats:
                            if f.get("vcodec") != "none" and f.get("url"):
                                if not best_f or (f.get("height") or 0) > (best_f.get("height") or 0):
                                    best_f = f
                        if best_f:
                            direct_url = best_f.get("url")
                        if not direct_url:
                            direct_url = entry.get("url")
                    else:
                        direct_url = entry.get("url")
                        if not direct_url and entry.get("thumbnails"):
                            direct_url = entry.get("thumbnails")[-1].get("url")

                    if not direct_url:
                        continue

                    if is_video_slide:
                        height = entry.get("height") or "HD"
                        res_label = f"{height}p" if isinstance(height, int) else str(height)
                        video_options.append({
                            "format_id": f"direct_video_slide_{slide_num}",
                            "resolution": res_label,
                            "ext": "mp4",
                            "type": "video",
                            "size": format_size(entry.get("filesize") or entry.get("filesize_approx") or 0) or "Unknown Size",
                            "label": f"Video {unit_label} {slide_num} ({res_label})",
                            "url": direct_url
                        })
                        slide_thumb = entry.get("thumbnail") or (
                            entry.get("thumbnails")[-1].get("url") if entry.get("thumbnails") else None
                        )
                        if slide_thumb:
                            images.append({
                                "label": f"{unit_label} {slide_num} Thumbnail",
                                "url": slide_thumb,
                                "ext": "jpg"
                            })
                    else:
                        images.append({
                            "label": f"{unit_label} {slide_num} Image",
                            "url": direct_url,
                            "ext": "jpg"
                        })
                        video_options.append({
                            "format_id": f"direct_photo_slide_{slide_num}",
                            "resolution": "Original",
                            "ext": "jpg",
                            "type": "image",
                            "size": "Unknown Size",
                            "label": f"Photo - {unit_label} {slide_num}",
                            "url": direct_url
                        })

                if video_options:
                    from concurrent.futures import ThreadPoolExecutor
                    client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt") if client_id else None
                    
                    def resolve_ytdl_slide_size(opt):
                        if opt.get("size") == "Unknown Size" or not opt.get("size"):
                            url_to_check = opt.get("url")
                            if url_to_check:
                                s_bytes = get_url_content_length(url_to_check, cookies_file=client_cookies)
                                if s_bytes:
                                    opt["size"] = format_size(s_bytes)

                    with ThreadPoolExecutor(max_workers=min(10, len(video_options))) as executor:
                        list(executor.map(resolve_ytdl_slide_size, video_options))

                if not video_options:
                    video_options.append({
                        "format_id": "bestvideo+bestaudio/best",
                        "resolution": "Best",
                        "ext": "mp4",
                        "type": "video",
                        "size": None,
                        "label": "Video (Best Quality)"
                    })
            else:
                # --- Find best audio stream for size estimation ---
                best_audio_format = None
                for f in formats_list:
                    if f.get("vcodec") == "none" and f.get("acodec") != "none":
                        if not best_audio_format or (f.get("tbr") or 0) > (best_audio_format.get("tbr") or 0):
                            best_audio_format = f

                best_audio_size = 0
                if best_audio_format:
                    best_audio_size = best_audio_format.get("filesize") or best_audio_format.get("filesize_approx") or 0
                    if not best_audio_size and duration_sec and best_audio_format.get("tbr"):
                        best_audio_size = int(duration_sec * best_audio_format.get("tbr") * 1000 / 8)
                if not best_audio_size and duration_sec:
                    best_audio_size = int(duration_sec * 128 * 1000 / 8)

                # --- Build video options ---
                added_resolutions = set()

                is_tiktok = "tiktok" in extractor or "tiktok" in url.lower()
                has_non_wm = False
                if is_tiktok:
                    for f in formats_list:
                        if f.get("vcodec") != "none":
                            f_id = str(f.get("format_id") or "").lower()
                            f_note = str(f.get("format_note") or "").lower()
                            is_wm = False
                            if "watermark" in f_id or "watermark" in f_note:
                                if "unwatermark" not in f_note:
                                    is_wm = True
                            if "wm_play" in f_id or f_id.startswith("wm-") or f_id.startswith("wm_"):
                                is_wm = True
                            if not is_wm:
                                has_non_wm = True
                                break

                target_formats = reversed(formats_list) if is_tiktok else formats_list

                for f in target_formats:
                    height = f.get("height")
                    vcodec = f.get("vcodec")
                    if height and vcodec and vcodec != "none":
                        if is_tiktok and has_non_wm:
                            f_id = str(f.get("format_id") or "").lower()
                            f_note = str(f.get("format_note") or "").lower()
                            is_wm = False
                            if "watermark" in f_id or "watermark" in f_note:
                                if "unwatermark" not in f_note:
                                    is_wm = True
                            if "wm_play" in f_id or f_id.startswith("wm-") or f_id.startswith("wm_"):
                                is_wm = True
                            if is_wm:
                                continue

                        res_label = f"{height}p"
                        if res_label not in added_resolutions:
                            v_size = f.get("filesize") or f.get("filesize_approx") or 0
                            if not v_size and duration_sec and f.get("tbr"):
                                v_size = int(duration_sec * f.get("tbr") * 1000 / 8)
                            total_size = v_size if is_tiktok else ((v_size + best_audio_size) if v_size else 0)

                            opt_dict = {
                                "format_id": f.get("format_id") if is_tiktok else f"bestvideo[height={height}]+bestaudio[ext=m4a]/bestvideo[height={height}]+bestaudio/best[height={height}]",
                                "resolution": res_label,
                                "ext": "mp4",
                                "type": "video",
                                "size": format_size(total_size) if total_size else "Unknown Size",
                                "label": f"Video {res_label}"
                            }
                            video_options.append(opt_dict)
                            added_resolutions.add(res_label)

                video_options.sort(key=lambda x: int(x["resolution"].replace("p", "")), reverse=True)

                if not video_options:
                    video_options.append({
                        "format_id": "bestvideo+bestaudio/best",
                        "resolution": "Best",
                        "ext": "mp4",
                        "type": "video",
                        "size": None,
                        "label": "Video (Best Quality)"
                    })

                # --- Build audio options ---
                # Native M4A (no conversion, ultra fast)
                est_m4a_size = format_size(best_audio_size) if best_audio_size else None
                audio_options.append({
                    "format_id": "bestaudio[ext=m4a]/bestaudio",
                    "resolution": "Audio",
                    "ext": "m4a",
                    "type": "audio",
                    "size": est_m4a_size,
                    "label": "M4A AAC (Original Quality - Fast)"
                })

                qualities = [
                    ("320", "Ultra", "320kbps"),
                    ("192", "High", "192kbps"),
                    ("128", "Standard", "128kbps"),
                ]
                for q_val, q_name, q_label in qualities:
                    est_size = format_size(int(duration_sec * int(q_val) * 1000 / 8)) if duration_sec else None
                    audio_options.append({
                        "format_id": "bestaudio/best",
                        "resolution": "Audio",
                        "ext": "mp3",
                        "type": "audio",
                        "quality": q_val,
                        "size": est_size,
                        "label": f"MP3 {q_name} ({q_label})"
                    })

            # --- Detect platform and source ---
            platform_class = "default"
            
            if "youtube" in extractor:
                if "youtubekids.com" in url:
                    platform_label = "YouTube Kids"
                    platform_class = "youtube-kids"
                elif "music.youtube.com" in url:
                    platform_label = "YouTube Music"
                    platform_class = "youtube-music"
                elif "/shorts/" in url or (not info.get("is_live") and info.get("duration", 0) and info.get("duration", 0) <= 60):
                    platform_label = "YouTube Shorts"
                    platform_class = "youtube-shorts"
                elif "/live/" in url or info.get("is_live"):
                    platform_label = "YouTube Live"
                    platform_class = "youtube-live"
                elif "/clip/" in url:
                    platform_label = "YouTube Clip"
                    platform_class = "youtube-clip"
                elif "/embed/" in url or "/v/" in url or "youtube-nocookie.com" in url:
                    platform_label = "YouTube Embed"
                    platform_class = "youtube"
                elif "m.youtube.com" in url:
                    platform_label = "YouTube Mobile"
                    platform_class = "youtube"
                else:
                    platform_label = "YouTube"
                    platform_class = "youtube"
            elif "tiktok" in extractor or "tiktok" in url.lower():
                is_tiktok_slideshow = False
                thumbnails_list = info.get("thumbnails") or []
                slide_urls = [t.get("url") for t in thumbnails_list if t.get("url") and t.get("url").startswith("http") and "avatar" not in t.get("url").lower()]
                if len(slide_urls) > 1:
                    is_tiktok_slideshow = True

                if "/story/" in url.lower() or "/stories/" in url.lower():
                    platform_label = "TikTok Story"
                    platform_class = "tiktok-story"
                elif is_tiktok_slideshow:
                    platform_label = "TikTok Slideshow"
                    platform_class = "tiktok-slideshow"
                else:
                    platform_label = "TikTok Video"
                    platform_class = "tiktok"
            elif "facebook" in extractor or "facebook" in url or "fb.watch" in url or "fb.gg" in url or "fb.com" in url:
                if "/reel/" in url or "/reels/" in url:
                    platform_label = "Facebook Reel"
                    platform_class = "facebook-reel"
                elif "/groups/" in url:
                    platform_label = "Facebook Group"
                    platform_class = "facebook-group"
                elif "/watch/live" in url or "/live" in url:
                    platform_label = "Facebook Live"
                    platform_class = "facebook-live"
                elif "/watch/" in url or "/videos/" in url:
                    platform_label = "Facebook Watch"
                    platform_class = "facebook-watch"
                elif "/stories/" in url:
                    platform_label = "Facebook Story"
                    platform_class = "facebook-story"
                elif "fb.gg" in url or "/gaming/" in url:
                    platform_label = "Facebook Gaming"
                    platform_class = "facebook-gaming"
                else:
                    platform_label = "Facebook"
                    platform_class = "facebook"
            elif "instagram" in extractor or is_instagram:
                if "/reel/" in url or "/reels/" in url:
                    platform_label = "Instagram Reel"
                    platform_class = "instagram-reel"
                elif "/stories/" in url:
                    platform_label = "Instagram Story"
                    platform_class = "instagram-story"
                elif "/tv/" in url:
                    platform_label = "Instagram TV"
                    platform_class = "instagram-tv"
                elif "/p/" in url:
                    platform_label = "Instagram Post"
                    platform_class = "instagram-post"
                else:
                    platform_label = "Instagram"
                    platform_class = "instagram"
            else:
                # Capitalize first letter of extractor
                raw_platform = info.get("extractor_key", "Video")
                platform_label = raw_platform.capitalize() if raw_platform else "Video"
                platform_class = "default"

            # --- Extract images / thumbnails ---
            if not images:
                images = []
            yt_id = info.get("id")
            if "youtube" in extractor and yt_id:
                images = [
                    {"label": "Max Resolution Thumbnail (1280x720)", "url": f"https://img.youtube.com/vi/{yt_id}/maxresdefault.jpg", "ext": "jpg"},
                    {"label": "Standard Quality Thumbnail (640x480)", "url": f"https://img.youtube.com/vi/{yt_id}/sddefault.jpg", "ext": "jpg"},
                    {"label": "High Quality Thumbnail (480x360)", "url": f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg", "ext": "jpg"},
                    {"label": "Medium Quality Thumbnail (320x180)", "url": f"https://img.youtube.com/vi/{yt_id}/mqdefault.jpg", "ext": "jpg"},
                    {"label": "Default Quality Thumbnail (120x90)", "url": f"https://img.youtube.com/vi/{yt_id}/default.jpg", "ext": "jpg"}
                ]
            else:
                thumbnails_list = info.get("thumbnails") or []
                is_tiktok = "tiktok" in extractor or "tiktok" in url.lower()
                is_tiktok_slideshow = False
                if is_tiktok:
                    slide_urls = [t.get("url") for t in thumbnails_list if t.get("url") and t.get("url").startswith("http") and "avatar" not in t.get("url").lower()]
                    if len(slide_urls) > 1:
                        is_tiktok_slideshow = True

                for idx, t in enumerate(thumbnails_list):
                    url_val = t.get("url")
                    if url_val and url_val.startswith("http"):
                        if is_tiktok_slideshow and "avatar" in url_val.lower():
                            continue
                        if not any(img["url"] == url_val for img in images):
                            label = f"Slide Photo {len(images)+1}" if is_tiktok_slideshow else f"Thumbnail {idx+1}"
                            images.append({
                                "label": label,
                                "url": url_val,
                                "ext": "jpg"
                            })
                if not images and thumbnail:
                    images.append({
                        "label": "Main Thumbnail",
                        "url": thumbnail,
                        "ext": "jpg"
                    })
            # Resolve sizes of TikTok video_options in parallel if they are Unknown Size or missing
            if is_tiktok and video_options:
                from concurrent.futures import ThreadPoolExecutor
                client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt") if client_id else None
                
                def resolve_tiktok_size(opt):
                    if opt.get("size") == "Unknown Size" or not opt.get("size"):
                        url_to_check = opt.get("url")
                        if url_to_check:
                            s_bytes = get_url_content_length(url_to_check, cookies_file=client_cookies)
                            if s_bytes:
                                opt["size"] = format_size(s_bytes)
                                
                with ThreadPoolExecutor(max_workers=min(10, len(video_options))) as executor:
                    list(executor.map(resolve_tiktok_size, video_options))

            return jsonify({
                "status": "success",
                "title": title,
                "uploader": uploader,
                "duration": duration,
                "thumbnail": thumbnail,
                "is_shorts": is_shorts,
                "platform_label": platform_label,
                "platform_class": platform_class,
                "views": views_label,
                "likes": likes_label,
                "upload_date": formatted_date,
                "description": description,
                "category": category,
                "tags": tags,
                "video_options": video_options,
                "audio_options": audio_options,
                "subtitles": subtitles,
                "images": images,
            })

    except Exception as e:
        logger.error(f"Error fetching metadata: {str(e)}")
        return jsonify({"status": "error", "message": f"Could not parse URL. {str(e)}"}), 500


def bg_download_task(download_id, url, format_id, ext, quality="192", title="media", client_id=None):
    """Background thread task to download media via yt-dlp."""
    temp_dir = os.path.join(TEMP_DOWNLOAD_DIR, f"temp_{download_id}")
    os.makedirs(temp_dir, exist_ok=True)
    logger.info(f"Task {download_id}: Start download {url} (format={format_id}, ext={ext}, quality={quality})")

    # Direct CDN stream download bypass
    if format_id.startswith("direct_video") or format_id.startswith("direct_photo") or format_id.startswith("direct_audio"):
        try:
            import requests
            import subprocess
            
            with downloads_status_lock:
                if download_id in downloads_status:
                    downloads_status[download_id].update({
                        "status": "downloading",
                        "progress": 5,
                        "message": "Connecting to direct stream source..."
                    })
                    
            referer = "https://www.facebook.com/"
            url_lower = url.lower()
            format_id_lower = str(format_id).lower()
            if "tiktok" in url_lower or "tiktok" in format_id_lower:
                referer = "https://www.tiktok.com/"
            elif "instagram" in url_lower:
                referer = "https://www.instagram.com/"
            elif "threads" in url_lower:
                referer = "https://www.threads.net/"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": referer
            }
            
            cookies_dict = {}
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
                                    name = parts[5]
                                    value = parts[6]
                                    cookies_dict[name] = value
                        logger.info(f"Loaded {len(cookies_dict)} cookies for direct CDN download task.")
                    except Exception as cookie_err:
                        logger.warning(f"Failed to parse cookies file {client_cookies}: {cookie_err}")

            response = requests.get(url, headers=headers, cookies=cookies_dict, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            is_audio_requested = ext in ["mp3", "m4a"]
            if is_audio_requested:
                download_ext = "mp4"
                filepath = os.path.join(temp_dir, f"temp_source.mp4")
            else:
                download_ext = ext
                filepath = os.path.join(temp_dir, f"media.{ext}")
                
            downloaded = 0
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=16384):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            if percent % 5 == 0 or percent == 100:
                                with downloads_status_lock:
                                    if download_id in downloads_status:
                                        downloads_status[download_id].update({
                                            "progress": min(80 if is_audio_requested else 95, percent),
                                            "message": f"Downloading direct file: {percent}%"
                                        })
                                        
            # Extract audio if requested
            if is_audio_requested:
                with downloads_status_lock:
                    if download_id in downloads_status:
                        downloads_status[download_id].update({
                            "progress": 85,
                            "message": "Extracting audio track..."
                        })
                        
                final_filepath = os.path.join(temp_dir, f"media.{ext}")
                
                if ext == "m4a":
                    # Try copying audio track directly
                    cmd = ["ffmpeg", "-y", "-i", filepath, "-vn", "-acodec", "copy", final_filepath]
                    res_cmd = subprocess.run(cmd, capture_output=True)
                    if res_cmd.returncode != 0:
                        logger.warning("ffmpeg audio copy failed, re-encoding to m4a...")
                        cmd = ["ffmpeg", "-y", "-i", filepath, "-vn", "-c:a", "aac", "-b:a", "192k", final_filepath]
                        subprocess.run(cmd, capture_output=True)
                else: # mp3
                    cmd = ["ffmpeg", "-y", "-i", filepath, "-vn", "-c:a", "libmp3lame", "-b:a", f"{quality}k", final_filepath]
                    subprocess.run(cmd, capture_output=True)
                    
                # Delete temp video source file
                try:
                    os.remove(filepath)
                except Exception:
                    pass
                    
                filepath = final_filepath
            
            def sanitize_filename(name):
                import re
                cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
                return cleaned[:80].strip() or "media"

            safe_title = sanitize_filename(title)
            user_filename = f"{safe_title}.{ext}"

            with downloads_status_lock:
                if download_id in downloads_status:
                    downloads_status[download_id].update({
                        "status": "complete",
                        "progress": 100,
                        "message": "Ready!",
                        "filepath": filepath,
                        "temp_dir": temp_dir,
                        "filename": user_filename,
                    })
                    logger.info(f"Task {download_id}: Complete. File: {user_filename}")
            
            schedule_cleanup(temp_dir, download_id, delay=300)
            return
            
        except Exception as e:
            logger.error(f"Direct download failed for task {download_id}: {e}")
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
            with downloads_status_lock:
                if download_id in downloads_status:
                    downloads_status[download_id].update({
                        "status": "error",
                        "progress": 0,
                        "message": f"Download failed: {str(e)}",
                        "error": str(e),
                    })
            return

    # Track how many times 'finished' fires
    # For video: finished fires once for video stream, once for audio stream
    # For audio/combined: finished fires once
    finished_count = [0]

    def progress_hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            pct = int((downloaded / total) * 100) if total > 0 else 0

            info = d.get("info_dict") or {}
            vcodec = info.get("vcodec")
            acodec = info.get("acodec")

            if ext in ["mp3", "m4a"]:
                # Audio-only: single stream, 0-90%
                progress_val = int(pct * 0.90)
                msg = f"Downloading audio stream: {pct}%"
            elif ext == "vtt":
                # Subtitle-only: single stream, 0-90%
                progress_val = int(pct * 0.90)
                msg = f"Downloading subtitles: {pct}%"
            else:
                is_video_only = (vcodec and vcodec != "none") and (not acodec or acodec == "none")
                is_audio_only = (not vcodec or vcodec == "none") and (acodec and acodec != "none")

                if is_video_only:
                    # Video stream (part 1/2): 0-70%
                    progress_val = int(pct * 0.70)
                    msg = f"Downloading video stream (1/2): {pct}%"
                elif is_audio_only:
                    # Audio stream (part 2/2): 70-90%
                    progress_val = 70 + int(pct * 0.20)
                    msg = f"Downloading audio stream (2/2): {pct}%"
                else:
                    # Combined/muxed stream: 0-90%
                    progress_val = int(pct * 0.90)
                    msg = f"Downloading: {pct}%"

            with downloads_status_lock:
                if download_id in downloads_status:
                    cur = downloads_status[download_id].get("progress", 0)
                    downloads_status[download_id].update({
                        "status": "downloading",
                        "progress": max(cur, progress_val),
                        "message": msg,
                    })

        elif d["status"] == "finished":
            finished_count[0] += 1
            with downloads_status_lock:
                if download_id in downloads_status:
                    if ext == "mp3":
                        # Audio: single stream done → encoding to MP3
                        downloads_status[download_id].update({
                            "status": "processing",
                            "progress": 95,
                            "message": "Converting to MP3...",
                        })
                    elif ext == "m4a":
                        # M4A: single stream done → finalizing (no conversion)
                        downloads_status[download_id].update({
                            "status": "processing",
                            "progress": 98,
                            "message": "Finalizing...",
                        })
                    elif ext == "vtt":
                        # Subtitles: single stream done → finalizing
                        downloads_status[download_id].update({
                            "status": "processing",
                            "progress": 98,
                            "message": "Finalizing subtitles...",
                        })
                    else:
                        if finished_count[0] == 1:
                            # First stream (video) done, audio coming next
                            # Check if this was a combined stream (both codecs present)
                            info = d.get("info_dict") or {}
                            vcodec = info.get("vcodec")
                            acodec = info.get("acodec")
                            is_combined = (vcodec and vcodec != "none") and (acodec and acodec != "none")
                            if is_combined:
                                # Combined stream — no merge needed
                                downloads_status[download_id].update({
                                    "status": "processing",
                                    "progress": 98,
                                    "message": "Finalizing...",
                                })
                            else:
                                # Video-only stream done → audio download starting
                                downloads_status[download_id].update({
                                    "status": "downloading",
                                    "progress": 70,
                                    "message": "Video stream complete. Downloading audio...",
                                })
                        else:
                            # Second stream (audio) done → merging
                            downloads_status[download_id].update({
                                "status": "merging",
                                "progress": 95,
                                "message": "Merging video and audio streams...",
                            })

    ydl_opts = {
        "outtmpl": os.path.join(temp_dir, "media.%(ext)s"),
        "nocheckcertificate": True,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "progress_hooks": [progress_hook],
        "js_runtimes": {"deno": {}, "node": {}, "bun": {}, "quickjs": {}},
        "cookiesfrombrowser": "auto",
        "ignoreerrors": True,
    }

    if ext == "mp3":
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality,
            }],
            "postprocessor_args": {
                "extractaudio": ["-compression_level", "9", "-threads", "0"]
            }
        })
    elif ext == "m4a":
        ydl_opts.update({
            "format": "bestaudio[ext=m4a]/bestaudio",
        })
    elif ext == "vtt":
        ydl_opts.update({
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [format_id],
        })
    else:
        ydl_opts.update({
            "format": format_id,
            "merge_output_format": "mp4",
        })

    try:
        try:
            with create_ydl_instance(ydl_opts, url, client_id) as ydl:
                ret_code = ydl.download([url])
                if ret_code != 0:
                    raise Exception(f"yt-dlp download returned non-zero code {ret_code}")
        except Exception as e:
            logger.warning(f"Download with cookies failed: {e}. Retrying without cookies...")
            ydl_opts_no_cookies = ydl_opts.copy()
            ydl_opts_no_cookies.pop("cookiefile", None)
            ydl_opts_no_cookies.pop("cookiesfrombrowser", None)
            with yt_dlp.YoutubeDL(ydl_opts_no_cookies) as ydl_nocookies:
                ret_nocookies = ydl_nocookies.download([url])
                if ret_nocookies != 0:
                    raise Exception(f"Fallback download also failed with code {ret_nocookies}")

        downloaded_files = os.listdir(temp_dir)
        if not downloaded_files:
            raise Exception("Download completed but no output file found.")

        filename_on_disk = downloaded_files[0]
        filepath = os.path.join(temp_dir, filename_on_disk)

        def sanitize_filename(name):
            import re
            cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
            return cleaned[:80].strip() or "media"

        safe_title = sanitize_filename(title)
        if ext == "vtt":
            user_filename = f"{safe_title}.{format_id}.vtt"
        else:
            user_filename = f"{safe_title}.{ext}"

        with downloads_status_lock:
            if download_id in downloads_status:
                downloads_status[download_id].update({
                    "status": "complete",
                    "progress": 100,
                    "message": "Ready!",
                    "filepath": filepath,
                    "temp_dir": temp_dir,
                    "filename": user_filename,
                })
                logger.info(f"Task {download_id}: Complete. File: {user_filename}")

        # Clean up the file 5 minutes (300 seconds) after completion
        schedule_cleanup(temp_dir, download_id, delay=300)

    except Exception as e:
        logger.error(f"Task {download_id} failed: {str(e)}")
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
        with downloads_status_lock:
            if download_id in downloads_status:
                downloads_status[download_id].update({
                    "status": "error",
                    "progress": 0,
                    "message": f"Download failed: {str(e)}",
                    "error": str(e),
                })


@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.get_json() or {}
    url = (data.get("url") or "").strip()
    if "tiktok.com" in url.lower() and "/photo/" in url.lower():
        import re
        url = re.sub(r'/photo/', '/video/', url, flags=re.IGNORECASE)
    format_id = (data.get("format_id") or "").strip()
    ext = (data.get("ext") or "mp4").strip()
    quality = (data.get("quality") or "192").strip()
    title = (data.get("title") or "media").strip()
    client_id = data.get("client_id")

    if not url or not format_id:
        return jsonify({"status": "error", "message": "URL and format_id are required."}), 400

    download_id = str(uuid.uuid4())

    with downloads_status_lock:
        downloads_status[download_id] = {
            "status": "pending",
            "progress": 0,
            "message": "Queued. Starting download...",
            "ext": ext,
            "filepath": None,
            "temp_dir": None,
            "filename": None,
            "error": None,
        }

    logger.info(f"Enqueued task {download_id} for {url} (client_id: {client_id})")
    thread = threading.Thread(target=bg_download_task, args=(download_id, url, format_id, ext, quality, title, client_id))
    thread.start()

    return jsonify({"status": "success", "download_id": download_id})


@app.route("/api/download/status/<download_id>", methods=["GET"])
def get_download_status(download_id):
    with downloads_status_lock:
        status_info = downloads_status.get(download_id)
    if not status_info:
        return jsonify({"status": "error", "message": "Download task not found."}), 404
    # Return a safe copy without internal paths
    return jsonify({
        "status": status_info["status"],
        "progress": status_info["progress"],
        "message": status_info["message"],
        "ext": status_info.get("ext", ""),
        "error": status_info.get("error"),
    })


@app.route("/api/download/file/<download_id>", methods=["GET"])
def get_download_file(download_id):
    with downloads_status_lock:
        status_info = downloads_status.get(download_id)

    if not status_info:
        return """
        <html>
            <head>
                <title>File Purged | EveryThingDownloader</title>
                <style>
                    body { background: #07080f; color: #8b9dc3; font-family: system-ui, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; text-align: center; }
                    .card { background: rgba(14, 17, 30, 0.55); border: 1px solid rgba(255, 255, 255, 0.06); padding: 32px; border-radius: 12px; max-width: 450px; box-shadow: 0 20px 50px rgba(0,0,0,0.5); backdrop-filter: blur(20px); }
                    h2 { color: #63b3ed; margin-top: 0; font-weight: 600; }
                    p { font-size: 0.9rem; line-height: 1.6; }
                </style>
            </head>
            <body>
                <div class="card">
                    <h2>File Purged from Server</h2>
                    <p>This file has already been downloaded and automatically deleted from the server storage to save disk space.</p>
                    <p>If you need another copy, please go back to the downloader page and click the <strong>Get</strong> button again to rebuild it.</p>
                </div>
            </body>
        </html>
        """, 404
    if status_info["status"] != "complete":
        return jsonify({"status": "error", "message": "File is not ready yet."}), 400

    filepath = status_info["filepath"]
    temp_dir = status_info["temp_dir"]
    filename = status_info["filename"]
    ext = filepath.rsplit(".", 1)[-1] if "." in filepath else "mp4"

    if not os.path.exists(filepath):
        return jsonify({"status": "error", "message": "File not found on server."}), 404

    file_size = os.path.getsize(filepath)

    def generate_chunks():
        try:
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    yield chunk
        finally:
            # Cleanup is handled by the 5-minute delayed timer to support retries and download manager calls
            pass

    fallback_filename = f"media.{ext}"
    encoded_filename = quote(filename)
    if ext == "mp3":
        content_type = "audio/mpeg"
    elif ext == "m4a":
        content_type = "audio/mp4"
    elif ext == "vtt":
        content_type = "text/vtt"
    else:
        content_type = "video/mp4"

    preview_mode = request.args.get("preview", "false").lower() == "true"

    from flask import send_file
    return send_file(
        filepath,
        mimetype=content_type,
        as_attachment=not preview_mode,
        download_name=filename,
        conditional=True
    )


@app.route("/api/download/image", methods=["GET"])
def download_image():
    url = request.args.get("url")
    filename = request.args.get("filename") or "image.jpg"
    client_id = request.args.get("client_id")
    if not url:
        return "Missing url parameter", 400
    try:
        import requests
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        cookies_dict = {}
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
                                name = parts[5]
                                value = parts[6]
                                cookies_dict[name] = value
                except Exception as cookie_err:
                    logger.warning(f"Failed to parse cookies file {client_cookies}: {cookie_err}")

        resp = requests.get(url, headers=headers, cookies=cookies_dict, stream=True, timeout=15)
        if resp.status_code == 200:
            from flask import Response
            fallback_filename = "image.jpg"
            encoded_filename = quote(filename)
            headers = {
                "Content-Disposition": f'attachment; filename="{fallback_filename}"; filename*=UTF-8\'\'{encoded_filename}',
                "Content-Type": resp.headers.get("Content-Type", "image/jpeg")
            }
            return Response(resp.content, headers=headers)
        else:
            return f"Failed to download image: HTTP {resp.status_code}", 500
    except Exception as e:
        return f"Error: {e}", 500


@app.route("/api/download/images/zip", methods=["POST"])
def download_images_zip():
    data = request.get_json() or {}
    urls = data.get("urls", [])
    title = data.get("title", "images")
    client_id = data.get("client_id")
    if not urls:
        return jsonify({"status": "error", "message": "No urls provided"}), 400
    try:
        import io
        import zipfile
        import requests
        
        cookies_dict = {}
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
                                name = parts[5]
                                value = parts[6]
                                cookies_dict[name] = value
                except Exception as cookie_err:
                    logger.warning(f"Failed to parse cookies file {client_cookies}: {cookie_err}")
        
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            for idx, item in enumerate(urls):
                url = item.get("url")
                label = item.get("label", f"image_{idx+1}")
                ext = item.get("ext", "jpg")
                if not url:
                    continue
                try:
                    req_headers = headers.copy()
                    if "tiktok" in url.lower() or "tiktokcdn" in url.lower():
                        req_headers["Referer"] = "https://www.tiktok.com/"
                    resp = requests.get(url, headers=req_headers, cookies=cookies_dict, timeout=10)
                    if resp.status_code == 200:
                        import re
                        safe_label = re.sub(r'[\\/*?:"<>|]', "", label).strip()
                        filename = f"{safe_label}.{ext}"
                        zf.writestr(filename, resp.content)
                except Exception as e:
                    logger.warning(f"Failed to zip image {url}: {e}")
                    
        memory_file.seek(0)
        from flask import send_file
        
        return send_file(
            memory_file,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{title}_images.zip"
        )
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to create ZIP: {e}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
