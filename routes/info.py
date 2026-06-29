import os
import re
import logging
import subprocess
import urllib.parse
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
import yt_dlp
try:
    from yt_dlp.networking.impersonate import ImpersonateTarget
except ImportError:
    ImpersonateTarget = None

from config import BASE_DIR, TEMP_DOWNLOAD_DIR
from utils.helpers import format_duration, format_size, get_referer_by_url, get_url_content_length
from utils.ytdl import create_ydl_instance, should_use_impersonate

from extractors import (
    extract_instagram_via_gallery_dl,
    extract_tiktok_slideshow_via_gallery_dl,
    extract_twitter_via_gallery_dl,
    extract_reddit_via_gallery_dl,
    scrape_reddit_fallback,
    parse_threads_page,
    extract_pinterest_via_gallery_dl,
    scrape_fb_post,
    extract_facebook_story,
    resolve_facebook_sizes,
    generic_html_link_harvester,
    resolve_hls_size
)

info_bp = Blueprint("info", __name__)
logger = logging.getLogger(__name__)


def strip_ansi_codes(text):
    if not text:
        return ""
    # Strip ANSI color/escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)




def save_bypass_domain(domain, reason="auto_learned"):
    if not domain or domain.replace('.', '').isdigit() or domain in ['localhost', '127.0.0.1']:
        return
    import sqlite3
    import time
    from config import DB_PATH
    try:
        domain_clean = domain.lower().lstrip("www.")
        conn = sqlite3.connect(DB_PATH, timeout=5.0)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO bypass_domains (domain, bypass_reason, timestamp) VALUES (?, ?, ?)",
            (domain_clean, reason, time.time())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Failed to save bypass domain {domain} to DB: {e}")

def should_bypass_ytdl(url):
    import urllib.parse
    import sqlite3
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        if ":" in domain:
            domain = domain.split(":")[0]
        if not domain:
            return False
            
        domain_clean = domain.lstrip("www.")
        
        # Query database
        from config import DB_PATH
        conn = sqlite3.connect(DB_PATH, timeout=5.0)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM bypass_domains WHERE domain = ? OR ? LIKE '%' || domain", (domain_clean, domain_clean))
        row = cursor.fetchone()
        conn.close()
        if row:
            return True
            
    except Exception as e:
        logger.warning(f"Error checking bypass domains: {e}")
    return False


def generic_html_link_harvester(url, client_id):
    from extractors.generic import generic_html_link_harvester as _harvester
    return _harvester(url, client_id)

@info_bp.route("/api/info", methods=["POST"])
def get_info():
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    if "tiktok.com" in url.lower() and "/photo/" in url.lower():
        url = re.sub(r'/photo/', '/video/', url, flags=re.IGNORECASE)
    client_id = data.get("client_id")

    # --- Local file / folder support ---
    if (os.path.isabs(url) or (len(url) >= 2 and url[1] == ':')) and os.path.exists(url):
        VIDEO_EXTS = {'mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm', 'ts', 'mpg', 'mpeg', 'm4v', '3gp'}
        AUDIO_EXTS = {'mp3', 'm4a', 'wav', 'flac', 'ogg', 'aac', 'wma', 'opus'}
        IMAGE_EXTS = {'jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'heic', 'heif', 'tiff', 'tif', 'svg', 'ico', 'avif'}
        SUBTITLE_EXTS = {'vtt', 'srt', 'ass', 'ssa', 'sub', 'idx', 'lrc'}
        TEXT_EXTS = {'txt', 'xml', 'json', 'csv', 'log', 'md', 'html', 'htm', 'css', 'js', 'py', 'yaml', 'yml', 'ini', 'cfg', 'conf'}

        def _detect_type(extension):
            if extension in VIDEO_EXTS:
                return 'video'
            elif extension in AUDIO_EXTS:
                return 'audio'
            elif extension in IMAGE_EXTS:
                return 'image'
            elif extension in SUBTITLE_EXTS:
                return 'subtitle'
            elif extension in TEXT_EXTS:
                return 'text'
            return 'other'

        import hashlib
        def _get_video_thumbnail(video_path):
            try:
                path_hash = hashlib.md5(video_path.encode('utf-8')).hexdigest()
                thumb_dir = os.path.join(TEMP_DOWNLOAD_DIR, "thumbnails")
                os.makedirs(thumb_dir, exist_ok=True)
                thumb_path = os.path.join(thumb_dir, f"{path_hash}.jpg")
                if os.path.exists(thumb_path):
                    return thumb_path.replace('\\', '/')
                
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", "00:00:01",
                    "-i", video_path,
                    "-vframes", "1",
                    "-f", "image2",
                    thumb_path
                ]
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, timeout=5)
                if res.returncode == 0 and os.path.exists(thumb_path):
                    return thumb_path.replace('\\', '/')
                
                # Fallback to -ss 00:00:00 if 1 second failed
                cmd[3] = "00:00:00"
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, timeout=5)
                if res.returncode == 0 and os.path.exists(thumb_path):
                    return thumb_path.replace('\\', '/')
            except Exception as ex:
                logging.error(f"Thumbnail generation failed: {ex}")
            return ""

        if os.path.isdir(url):
            entries = []
            for fname in os.listdir(url):
                full_path = os.path.join(url, fname)
                if not os.path.isfile(full_path):
                    continue
                file_ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
                file_size = os.path.getsize(full_path)
                entries.append({
                    "title": fname,
                    "path": full_path.replace('\\', '/'),
                    "ext": file_ext,
                    "size": format_size(file_size),
                    "size_bytes": file_size,
                    "type": _detect_type(file_ext)
                })
            entries.sort(key=lambda e: e["title"].lower())
            
            # Smart thumbnail selection for local directories
            folder_thumbnail = ""
            first_image = next((e for e in entries if e["type"] == "image"), None)
            if first_image:
                folder_thumbnail = first_image["path"]
            else:
                first_video = next((e for e in entries if e["type"] == "video"), None)
                if first_video:
                    folder_thumbnail = _get_video_thumbnail(first_video["path"])
                    
            # Collect folder images for the frontend image grid view
            folder_images = []
            for entry in entries:
                if entry["type"] == "image":
                    folder_images.append({
                        "url": entry["path"],
                        "label": entry["title"],
                        "ext": entry["ext"]
                    })

            return jsonify({
                "status": "success",
                "is_local": True,
                "is_playlist": True,
                "title": os.path.basename(url),
                "uploader": url.replace('\\', '/'),
                "duration": f"{len(entries)} files",
                "thumbnail": folder_thumbnail,
                "platform_label": "Local Folder",
                "platform_class": "local",
                "entries": entries,
                "video_options": [],
                "audio_options": [],
                "subtitles": {},
                "images": folder_images
            })
        else:
            filepath = os.path.abspath(url)
            filename = os.path.basename(filepath)
            file_size = os.path.getsize(filepath)
            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            detected_type = _detect_type(ext)
            local_url = filepath.replace('\\', '/')
            file_option = {
                "format_id": "local_file",
                "label": filename,
                "resolution": "",
                "ext": ext,
                "url": local_url,
                "size": format_size(file_size),
                "type": detected_type,
                "quality": "",
                "is_local": True
            }
            video_opts = []
            audio_opts = []
            images_list = []
            thumbnail_url = ""
            if detected_type == 'audio':
                file_option["format_id"] = "direct_audio_local"
                audio_opts.append(file_option)
            elif detected_type == 'image':
                thumbnail_url = local_url
                images_list.append({
                    "url": local_url,
                    "label": filename,
                    "resolution": "",
                    "size": format_size(file_size)
                })
                # Also add as video_option for direct download
                file_option["format_id"] = "image_download"
                video_opts.append(file_option)
            else:
                # video, subtitle, text, other — put in video_options
                if detected_type == 'video':
                    file_option["format_id"] = "direct_video_local"
                    thumbnail_url = _get_video_thumbnail(filepath)
                video_opts.append(file_option)
                
            return jsonify({
                "status": "success",
                "is_local": True,
                "title": filename,
                "uploader": os.path.dirname(filepath).replace('\\', '/'),
                "duration": format_size(file_size),
                "thumbnail": thumbnail_url,
                "platform_label": "Local File",
                "platform_class": "local",
                "video_options": video_opts,
                "audio_options": audio_opts,
                "subtitles": {},
                "images": images_list
            })
    # --- End local file / folder support ---

    original_pexels_url = None
    if "pexels.com" in url.lower():
        match_px_v = re.search(r"/download/video/(\d+)", url)
        if match_px_v:
            original_pexels_url = url
            url = f"https://www.pexels.com/video/{match_px_v.group(1)}/"
            logger.info(f"Normalizing Pexels download URL to video page: {url}")
        else:
            match_px_p = re.search(r"/download/photo/(\d+)", url)
            if match_px_p:
                original_pexels_url = url
                url = f"https://www.pexels.com/photo/{match_px_p.group(1)}/"
                logger.info(f"Normalizing Pexels download URL to photo page: {url}")

    if not url:
        return jsonify({"status": "error", "message": "Link URL is required."}), 400

    is_twitter = "twitter.com" in url.lower() or "x.com" in url.lower()
    twitter_gallery_fallback = None
    if is_twitter:
        try:
            logger.info("Twitter/X URL detected. Attempting extraction via gallery-dl first...")
            gallery_info = extract_twitter_via_gallery_dl(url, client_id)
            if gallery_info:
                # Check if this tweet has video options
                has_video = False
                for opt in gallery_info.get("video_options", []):
                    if opt.get("type") == "video":
                        has_video = True
                        break
                
                if not has_video:
                    logger.info("Successfully extracted Twitter/X photo post using gallery-dl.")
                    return jsonify(gallery_info)
                else:
                    logger.info("Twitter/X video post detected. Deferring to yt-dlp for full metadata and thumbnail extraction.")
                    twitter_gallery_fallback = gallery_info
        except Exception as gallery_e:
            logger.warning(f"Primary gallery-dl Twitter/X extraction failed: {gallery_e}. Falling back to yt-dlp...")
            if any(keyword in str(gallery_e).lower() for keyword in ["login", "redirect", "cookie"]):
                return jsonify({
                    "status": "error",
                    "message": "This Twitter/X post requires an account cookie to access or is age-restricted. Please log in to Twitter/X in your browser, export and upload a J2TEAM cookie file (choose Netscape or JSON format) to continue."
                }), 400

    is_reddit = "reddit.com" in url.lower() or "redd.it" in url.lower()
    reddit_gallery_fallback = None
    if is_reddit:
        # Pre-resolve Reddit share links (/r/xxx/s/xxx) to canonical /comments/ URLs
        is_share_link = re.match(r"https?://(?:www\.|old\.|new\.)?reddit\.com/r/[^/]+/s/[^/?]+", url)
        if is_share_link:
            try:
                import requests as req_resolve
                resolve_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
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
                                        cookies_dict[parts[5]] = parts[6]
                        except Exception as cookie_err:
                            logger.warning(f"Failed to parse cookies for Reddit share resolution: {cookie_err}")
                resolve_res = req_resolve.get(url, headers=resolve_headers, cookies=cookies_dict, timeout=15, allow_redirects=True)
                resolved_url = resolve_res.url
                logger.info(f"Reddit share link resolved: {url} -> {resolved_url}")
                url = resolved_url
            except Exception as resolve_e:
                logger.warning(f"Failed to resolve Reddit share link: {resolve_e}")
        
        gallery_info = None
        try:
            logger.info("Reddit URL detected. Attempting extraction via gallery-dl first...")
            gallery_info = extract_reddit_via_gallery_dl(url, client_id)
        except Exception as gallery_e:
            logger.warning(f"Primary gallery-dl Reddit extraction failed: {gallery_e}. Trying fallback scraper...")
            
        if not gallery_info:
            try:
                gallery_info = scrape_reddit_fallback(url, client_id)
            except Exception as fallback_e:
                logger.error(f"Reddit fallback scraper failed: {fallback_e}")
                gallery_info = None
                
        if gallery_info:
            # Check if this post has video options
            has_video = False
            for opt in gallery_info.get("video_options", []):
                if opt.get("type") == "video":
                    has_video = True
                    break
            
            if not has_video:
                logger.info("Successfully extracted Reddit photo post.")
                return jsonify(gallery_info)
            else:
                logger.info("Reddit video post detected. Deferring to yt-dlp first.")
                reddit_gallery_fallback = gallery_info

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

    is_pinterest = "pinterest.com" in url.lower() or "pin.it" in url.lower() or "pinimg.com" in url.lower()
    pinterest_gallery_fallback = None
    if is_pinterest:
        try:
            logger.info("Pinterest URL detected. Attempting extraction via gallery-dl first...")
            gallery_info = extract_pinterest_via_gallery_dl(url, client_id)
            if gallery_info:
                has_video = False
                for opt in gallery_info.get("video_options", []):
                    if opt.get("type") == "video":
                        has_video = True
                        break
                if not has_video:
                    logger.info("Successfully extracted Pinterest photo post using gallery-dl.")
                    return jsonify(gallery_info)
                else:
                    logger.info("Pinterest video post detected. Deferring to yt-dlp for potential higher quality / metadata.")
                    pinterest_gallery_fallback = gallery_info
        except Exception as gallery_e:
            logger.warning(f"Primary gallery-dl Pinterest extraction failed: {gallery_e}. Falling back to yt-dlp...")

    is_instagram = "instagram.com" in url.lower() or "instagr.am" in url.lower()
    if is_instagram:
        lower_url = url.lower()
        if not any(path in lower_url for path in ["/p/", "/reel/", "/reels/", "/stories/", "/tv/"]):
            return jsonify({
                "status": "error",
                "message": "Please enter a link to a specific Post, Reel, Story, or TV on Instagram instead of a user's profile."
            }), 400

    if "/stories/" in url and ("facebook.com" in url or "fb.com" in url or "fb.watch" in url):
        try:
            result = extract_facebook_story(url, client_id)
            return jsonify(result)
        except ValueError as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 400
        except PermissionError as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 400
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
        # For video-specific URLs, prefer yt-dlp (better HD + metadata support)
        # Custom scraper is primarily for photo posts which yt-dlp cannot handle
        is_fb_video_url = any(p in url.lower() for p in ["/share/v/", "/share/r/", "/videos/", "/reel/", "/reels/", "/watch", "fb.watch"])
        
        if not is_fb_video_url:
            try:
                logger.info(f"Facebook Post URL detected. Attempting custom scraping via facebookexternalhit: {url}")
                fb_info = scrape_fb_post(url, client_id)
                if fb_info and fb_info.get("status") == "success" and (fb_info.get("images") or fb_info.get("video_options")):
                    # Resolve sizes of video_options in parallel using ThreadPoolExecutor
                    video_options = fb_info.get("video_options", [])
                    if video_options:
                        resolve_facebook_sizes(video_options, client_id)
                            
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
                    "message": "This TikTok Video or Slideshow requires account cookies or the system IP is blocked (captcha encountered). Please log in to TikTok in your browser, export and upload a J2TEAM cookie file (Netscape or JSON format) to continue."
                }), 400

    # Direct bypass for movie/streaming sites to avoid slow yt-dlp timeout delays
    if should_bypass_ytdl(url):
        logger.info(f"Movie/streaming site detected via bypass rule: {url}. Bypassing yt-dlp and routing directly to generic harvester.")
        harvester_info = generic_html_link_harvester(url, client_id)
        if harvester_info:
            video_opts = harvester_info.get("video_options", [])
            has_streams = any(opt.get("format_id") != "generic_fallback" for opt in video_opts)
            if has_streams:
                try:
                    parsed_h = urllib.parse.urlparse(url)
                    domain_h = parsed_h.netloc.lower().split(":")[0].lstrip("www.")
                    save_bypass_domain(domain_h, "successful_harvest")
                except Exception:
                    pass
            return jsonify(harvester_info)

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
                    "message": "Instagram requires account cookies to access. Please export and upload a J2TEAM cookie file (Netscape or JSON format) to continue."
                }), 400

    is_youtube = any(domain in url.lower() for domain in ["youtube.com", "youtu.be"])
    ydl_opts = {
        "verbose": is_youtube,
        "quiet": not is_youtube,
        "no_warnings": not is_youtube,
        "nocheckcertificate": True,
        "noplaylist": not is_instagram,
        "js_runtimes": {"deno": {}, "node": {}, "bun": {}, "quickjs": {}},
        "cookiesfrombrowser": "auto",
        "ignoreerrors": False,
        "compat_opts": {"prefer-legacy-http-handler"},
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "android", "web_creator", "mweb", "default"],
            },
            "generic": {
                "impersonate": [""]
            }
        },
    }
    if should_use_impersonate():
        try:
            ydl_opts["impersonate"] = ImpersonateTarget.from_str("chrome")
        except Exception as e:
            logger.warning(f"Could not set impersonate option in get_info: {e}")

    try:
        info = None
        first_err = None
        tried_facebook_no_cookies = False
        try:
            if is_facebook:
                logger.info("Facebook URL detected. Trying metadata extraction WITHOUT cookies first...")
                tried_facebook_no_cookies = True
                ydl_opts_nocookies = ydl_opts.copy()
                ydl_opts_nocookies.pop("cookiefile", None)
                ydl_opts_nocookies.pop("cookiesfrombrowser", None)
                with yt_dlp.YoutubeDL(ydl_opts_nocookies) as ydl_nocookies:
                    info = ydl_nocookies.extract_info(url, download=False)
            else:
                with create_ydl_instance(ydl_opts, url, client_id) as ydl:
                    info = ydl.extract_info(url, download=False)
        except Exception as e:
            first_err = e
            if original_pexels_url:
                logger.warning(f"Failed to extract from normalized Pexels page: {e}. Reverting to original download URL: {original_pexels_url}")
                url = original_pexels_url
                try:
                    with create_ydl_instance(ydl_opts, url, client_id) as ydl:
                        info = ydl.extract_info(url, download=False)
                except Exception as pex_e:
                    logger.warning(f"Pexels download link extraction with cookies failed: {pex_e}")
            
            if not info:
                if is_facebook:
                    logger.warning(f"Facebook metadata extraction without cookies failed: {e}. Will retry with cookies...")
                else:
                    logger.warning(f"Metadata extraction with cookies failed: {e}. Retrying without cookies...")

        # Check if Facebook info is low quality (partial extraction)
        if info and is_facebook:
            fb_title = (info.get("title") or "").strip().lower()
            fb_thumb = info.get("thumbnail")
            fb_duration = info.get("duration")
            fb_generic_titles = ["facebook", "facebook video", "watch", ""]
            if fb_title in fb_generic_titles or (not fb_thumb and not fb_duration):
                if tried_facebook_no_cookies:
                    logger.warning(f"Facebook metadata without cookies appears incomplete (title='{info.get('title')}', thumbnail={bool(fb_thumb)}, duration={fb_duration}). Discarding and will retry with cookies...")
                else:
                    logger.warning(f"Facebook metadata with cookies appears incomplete. Discarding and retrying without cookies...")
                info = None

        if not info:
            logger.info("Retrying metadata extraction with alternate configuration...")
            try:
                if is_facebook and tried_facebook_no_cookies:
                    logger.info("Retrying Facebook metadata extraction WITH cookies...")
                    with create_ydl_instance(ydl_opts, url, client_id) as ydl:
                        info = ydl.extract_info(url, download=False)
                    if info:
                        fb_title = (info.get("title") or "").strip().lower()
                        fb_thumb = info.get("thumbnail")
                        fb_duration = info.get("duration")
                        fb_generic_titles = ["facebook", "facebook video", "watch", ""]
                        if fb_title in fb_generic_titles or (not fb_thumb and not fb_duration):
                            logger.warning("Facebook metadata with cookies also appears incomplete. Discarding...")
                            info = None
                    if not info:
                        raise Exception("Facebook metadata from cookies is incomplete or low quality")
                else:
                    ydl_opts_nocookies = ydl_opts.copy()
                    ydl_opts_nocookies.pop("cookiefile", None)
                    ydl_opts_nocookies.pop("cookiesfrombrowser", None)
                    with yt_dlp.YoutubeDL(ydl_opts_nocookies) as ydl_nocookies:
                        info = ydl_nocookies.extract_info(url, download=False)
            except Exception as nocookie_e:
                logger.error(f"Metadata extraction retry/fallback failed: {nocookie_e}")
                
                if is_reddit and reddit_gallery_fallback:
                    logger.info("yt-dlp failed for Reddit. Falling back to pre-extracted gallery-dl info.")
                    return jsonify(reddit_gallery_fallback)
                if is_twitter and twitter_gallery_fallback:
                    logger.info("yt-dlp failed for Twitter. Falling back to pre-extracted gallery-dl info.")
                    return jsonify(twitter_gallery_fallback)
                if is_pinterest and pinterest_gallery_fallback:
                    logger.info("yt-dlp failed for Pinterest. Falling back to pre-extracted gallery-dl info.")
                    return jsonify(pinterest_gallery_fallback)
                    
                err_str = f"{str(first_err)} | {str(nocookie_e)}".lower()
                
                is_twitter = "twitter.com" in url.lower() or "x.com" in url.lower()
                if is_twitter:
                    twitter_auth_keywords = ["login", "redirect", "cookie", "keyerror", "result", "guest", "authentication", "rate limit", "403", "429", "no video could be found"]
                    if any(keyword in err_str for keyword in twitter_auth_keywords):
                        return jsonify({
                            "status": "error",
                            "message": "This Twitter/X post requires login cookies to access (Twitter blocks anonymous viewing completely). Please log in to Twitter/X in your browser, export and upload a J2TEAM cookie file (Netscape or JSON format) in the 'Manage Cookies' section to continue."
                        }), 400

                is_soundcloud = "soundcloud.com" in url.lower()
                if is_soundcloud:
                    if any(k in err_str for k in ["geo", "restricted", "location", "country", "blocked", "copyright"]):
                        return jsonify({
                            "status": "error",
                            "message": "This SoundCloud content is geo-restricted or blocked due to copyright in the server's location. Please try again later or use a proxy/VPN at a different location."
                        }), 400
                
                is_facebook = any(domain in url.lower() for domain in ["facebook.com", "fb.com", "fb.watch", "fb.gg"])
                if is_facebook:
                    # Try custom scraper as last resort before returning error
                    try:
                        logger.info("yt-dlp failed for Facebook. Trying custom scraper as fallback...")
                        fb_fallback = scrape_fb_post(url, client_id)
                        if fb_fallback and fb_fallback.get("status") == "success" and (fb_fallback.get("images") or fb_fallback.get("video_options")):
                            video_options = fb_fallback.get("video_options", [])
                            if video_options:
                                resolve_facebook_sizes(video_options, client_id)
                            logger.info(f"Custom scraper fallback succeeded for Facebook. Options: {len(video_options)}")
                            return jsonify(fb_fallback)
                    except Exception as fb_fallback_err:
                        logger.warning(f"Custom scraper fallback also failed: {fb_fallback_err}")
                    
                    fb_auth_keywords = [
                        "registered users",
                        "log in",
                        "login",
                        "sign in",
                        "private",
                        "permission",
                        "cookies",
                        "cookies-from-browser",
                        "cannot parse data",
                        "unable to extract",
                        "cannot parse",
                        "parser",
                        "redirect"
                    ]
                    if any(keyword in err_str for keyword in fb_auth_keywords):
                        return jsonify({
                            "status": "error",
                            "message": "Facebook requires account cookies to access this post/video (it might be private, restricted, or in a closed group). Please log in to Facebook in your browser, export and upload a J2TEAM cookie file (Netscape or JSON format) to continue."
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
                            "message": "YouTube requires identity verification (Sign in / Confirm you are not a bot) or this video is private/age-restricted. Please export and upload a J2TEAM cookie file (Netscape or JSON format) to continue."
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
                            "message": "This TikTok Video or Slideshow requires account cookies or the system IP is blocked (captcha encountered). Please log in to TikTok in your browser, export and upload a J2TEAM cookie file (Netscape or JSON format) to continue."
                        }), 400

                is_reddit = "reddit.com" in url.lower() or "redd.it" in url.lower()
                if is_reddit:
                    reddit_auth_keywords = [
                        "authentication is required",
                        "username and password",
                        "cookies",
                        "cookies-from-browser",
                        "sign in",
                        "login",
                        "log in",
                        "rate limit",
                        "403",
                        "429"
                    ]
                    if any(keyword in err_str for keyword in reddit_auth_keywords):
                        return jsonify({
                            "status": "error",
                            "message": "Reddit requires account cookies or the system IP is rate-limited. Please log in to Reddit in your browser, export and upload a J2TEAM cookie file (Netscape or JSON format) to continue."
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
                                "message": "Instagram requires account cookies to access. Please export and upload a J2TEAM cookie file (Netscape or JSON format) to continue."
                            }), 400

                if "there is no video in this post" in err_str:
                    return jsonify({
                        "status": "error",
                        "message": "Unable to load image information from Instagram. Instagram may require account cookies to access this post. Please upload a J2TEAM cookie file (Netscape or JSON format) to continue."
                    }), 400
                if is_instagram and any(keyword in err_str for keyword in ["login", "logged-in", "cookies", "redirect", "confirm your age", "challenge", "checkpoint", "sign in", "rate limit", "empty media", "unable to extract"]):
                    return jsonify({
                        "status": "error",
                        "message": "Instagram requires account cookies to access. Please export and upload a J2TEAM cookie file (Netscape or JSON format) to continue."
                    }), 400
                if is_reddit and reddit_gallery_fallback:
                    logger.info("yt-dlp failed for Reddit video. Falling back to pre-extracted gallery-dl info.")
                    return jsonify(reddit_gallery_fallback)
                if is_twitter and twitter_gallery_fallback:
                    logger.info("yt-dlp failed for Twitter video. Falling back to pre-extracted gallery-dl info.")
                    return jsonify(twitter_gallery_fallback)
                if is_pinterest and pinterest_gallery_fallback:
                    logger.info("yt-dlp failed for Pinterest video. Falling back to pre-extracted gallery-dl info.")
                    return jsonify(pinterest_gallery_fallback)
                known_domains = [
                    "youtube.com", "youtu.be", "youtubekids.com", "youtube-nocookie.com",
                    "facebook.com", "fb.com", "fb.watch", "fb.gg",
                    "instagram.com", "instagr.am",
                    "tiktok.com",
                    "twitter.com", "x.com",
                    "threads.net", "threads.com",
                    "reddit.com", "redd.it",
                    "pinterest.com", "pin.it", "pinimg.com",
                    "soundcloud.com"
                ]
                is_known_platform = any(domain in url.lower() for domain in known_domains)
                if is_known_platform:
                    return jsonify({
                        "status": "error",
                        "message": f"Unable to extract media metadata: {strip_ansi_codes(str(nocookie_e))}"
                    }), 400

                harvester_info = generic_html_link_harvester(url, client_id)
                if harvester_info:
                    video_opts = harvester_info.get("video_options", [])
                    has_streams = any(opt.get("format_id") != "generic_fallback" for opt in video_opts)
                    if has_streams:
                        try:
                            parsed_h = urllib.parse.urlparse(url)
                            domain_h = parsed_h.netloc.lower().split(":")[0].lstrip("www.")
                            save_bypass_domain(domain_h, "successful_harvest")
                        except Exception:
                            pass
                    logger.info(f"Generic HTML link harvester succeeded for {url} (nocookie_e). Found {len(video_opts)} options.")
                    return jsonify(harvester_info)
                return jsonify({
                    "status": "error",
                    "message": f"Unable to extract media metadata: {strip_ansi_codes(str(nocookie_e))}"
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
                            "message": "Instagram requires account cookies to access. Please export and upload a J2TEAM cookie file (Netscape or JSON format) to continue."
                        }), 400
                return jsonify({
                    "status": "error",
                    "message": "Instagram requires account cookies to access. Please export and upload a J2TEAM cookie file (Netscape or JSON format) to continue."
                }), 400
            if is_reddit and reddit_gallery_fallback:
                logger.info("yt-dlp returned no info for Reddit video. Falling back to pre-extracted gallery-dl info.")
                return jsonify(reddit_gallery_fallback)
            if is_twitter and twitter_gallery_fallback:
                logger.info("yt-dlp returned no info for Twitter video. Falling back to pre-extracted gallery-dl info.")
                return jsonify(twitter_gallery_fallback)
            if is_pinterest and pinterest_gallery_fallback:
                logger.info("yt-dlp returned no info for Pinterest video. Falling back to pre-extracted gallery-dl info.")
                return jsonify(pinterest_gallery_fallback)
            known_domains = [
                "youtube.com", "youtu.be", "youtubekids.com", "youtube-nocookie.com",
                "facebook.com", "fb.com", "fb.watch", "fb.gg",
                "instagram.com", "instagr.am",
                "tiktok.com",
                "twitter.com", "x.com",
                "threads.net", "threads.com",
                "reddit.com", "redd.it",
                "pinterest.com", "pin.it", "pinimg.com",
                "soundcloud.com"
            ]
            is_known_platform = any(domain in url.lower() for domain in known_domains)
            if is_known_platform:
                return jsonify({
                    "status": "error",
                    "message": "Failed to extract media metadata from this platform."
                }), 400

            harvester_info = generic_html_link_harvester(url, client_id)
            if harvester_info:
                video_opts = harvester_info.get("video_options", [])
                has_streams = any(opt.get("format_id") != "generic_fallback" for opt in video_opts)
                if has_streams:
                    try:
                        parsed_h = urllib.parse.urlparse(url)
                        domain_h = parsed_h.netloc.lower().split(":")[0].lstrip("www.")
                        save_bypass_domain(domain_h, "successful_harvest")
                    except Exception:
                        pass
                logger.info(f"Generic HTML link harvester succeeded for {url} (not info). Found {len(video_opts)} options.")
                return jsonify(harvester_info)
            return jsonify({
                "status": "error",
                "message": "Failed to extract media metadata."
            }), 400

        if True:
            if info and not is_instagram and info.get("entries"):
                logger.info("Non-Instagram playlist/multi-entry response detected. Promoting first entry as primary media info.")
                entries = info.get("entries", [])
                if entries and entries[0]:
                    main_title = info.get("title")
                    main_thumb = info.get("thumbnail")
                    info = entries[0]
                    if not info.get("title") and main_title:
                        info["title"] = main_title
                    if not info.get("thumbnail") and main_thumb:
                        info["thumbnail"] = main_thumb

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
                                "message": "Instagram requires account cookies to access. Please export and upload a J2TEAM cookie file (Netscape or JSON format) to continue."
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
                                    "message": "This TikTok Video or Slideshow requires account cookies or the system IP is blocked (captcha encountered). Please log in to TikTok in your browser, export and upload a J2TEAM cookie file (Netscape or JSON format) to continue."
                                }), 400

            extractor = info.get("extractor_key", "").lower() if info.get("extractor_key") else ""

            title = info.get("title", "Unknown Title")

            # Strip trailing duplicate file markers (e.g., (1), (2))
            if title and title != "Unknown Title":
                title = re.sub(r"\s*\(\d+\)\s*$", "", title).strip()

            # Clean up SEO marketing text and site brand suffixes from title
            if title and title != "Unknown Title":
                # 1. Remove brand suffixes
                brand_suffixes = [
                    r"\s*-\s*Pikbest", r"\s*\|\s*Pikbest",
                    r"\s*-\s*Pixabay", r"\s*\|\s*Pixabay",
                    r"\s*-\s*YouTube", r"\s*\|\s*YouTube",
                ]
                for pattern in brand_suffixes:
                    title = re.compile(pattern, re.IGNORECASE).sub("", title)
                
                # 2. Clean up Pikbest specific prefixes/suffixes
                if "pikbest" in url.lower() or "pikbest" in title.lower():
                    pikbest_prefixes = [
                        r"^Tải\s+miễn\s+phí\s+mẫu\s*",
                        r"^Tải\s+mẫu\s*",
                        r"^Mẫu\s*\|\s*",
                        r"^Mẫu\s*",
                        r"^Tải\s+miễn\s+phí\s*",
                    ]
                    for pattern in pikbest_prefixes:
                        title = re.compile(pattern, re.IGNORECASE).sub("", title)
                    
                    title = re.compile(r"\s*Video\s+(PRPROJ|AEP|PSD|AI|CDR|MAX|C4D|PPT|DOC|XLS)\s*$", re.IGNORECASE).sub("", title)
                
                # 3. Clean up Pexels generic names
                if "pexels.com" in url.lower() or "pexels" in original_url.lower() or "pexels" in title.lower():
                    url_to_check = original_pexels_url or original_url or url
                    url_id_match = re.search(r"/(?:video|photo|download/video|download/photo)/(\d+)", url_to_check)
                    if url_id_match:
                        url_id = url_id_match.group(1)
                        if "photo" in url_to_check.lower():
                            title = f"Pexels Photo {url_id}"
                        else:
                            title = f"Pexels Video {url_id}"
                    else:
                        if re.match(r"^pexels-photo-\d+$", title, re.IGNORECASE):
                            title = "Pexels Photo " + title.split("-")[-1]
                        elif re.match(r"^\d+_\d+_\d+_\d+fps$", title, re.IGNORECASE):
                            title = "Pexels Video " + title.split("_")[0]
                        elif re.match(r"^\d+-[a-zA-Z0-9_]+$", title, re.IGNORECASE):
                            title = "Pexels Video " + title.split("-")[0]

            duration_sec = info.get("duration", 0)
            duration = format_duration(duration_sec)

            uploader = info.get("uploader")
            if not uploader or uploader == "Unknown Channel":
                try:
                    import urllib.parse
                    parsed = urllib.parse.urlparse(url)
                    uploader = parsed.netloc.lower().lstrip("www.")
                except Exception:
                    uploader = "Unknown Channel"
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
                                res = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=15)
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
                    est_bytes = int(float(duration_sec) * 50) + 100
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
            # Auto captions
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
            ext_lower = (info.get("ext") or "").lower()
            is_generic = (extractor == "generic" or info.get("extractor_key") == "Generic" or not extractor)
            is_direct_image = is_generic and ext_lower in ["jpg", "jpeg", "png", "webp", "gif", "bmp", "tiff", "svg"]
            is_direct_audio = is_generic and ext_lower in ["mp3", "wav", "m4a", "flac", "aac", "ogg", "opus"]
            is_direct_video = is_generic and ext_lower in ["mp4", "mkv", "webm", "avi", "mov", "flv"]
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
                    best_url = info.get("url")
                    if not best_url and formats_list:
                        best_url = formats_list[-1].get("url") if formats_list else None
                    is_fallback_direct = best_url and best_url.startswith("http") and best_url != url
                    fmt_id = "direct_video" if is_fallback_direct else "bestvideo+bestaudio/best"
                    video_options.append({
                        "format_id": fmt_id,
                        "resolution": "Best",
                        "ext": "mp4",
                        "type": "video",
                        "size": None,
                        "label": "Video (Best Quality)",
                        "url": best_url
                    })
            else:
                if is_direct_image:
                    thumbnail = url
                    category = "Image File"
                    img_size = info.get("filesize") or info.get("filesize_approx") or 0
                    video_options.append({
                        "format_id": "direct_image",
                        "resolution": "Original",
                        "ext": ext_lower,
                        "type": "image",
                        "size": format_size(img_size) if img_size else "Unknown Size",
                        "label": f"Image File ({ext_lower.upper()})",
                        "url": url
                    })
                    images.append({
                        "label": "Image File",
                        "url": url,
                        "ext": ext_lower
                    })
                else:
                    if is_direct_video:
                        category = "Video File"
                        # Generate thumbnail dynamically using ffmpeg if not already cached
                        try:
                            import hashlib
                            import static_ffmpeg
                            
                            video_stream_url = info.get("url")
                            if not video_stream_url and formats_list:
                                video_stream_url = formats_list[-1].get("url")
                            if not video_stream_url:
                                video_stream_url = url
                            
                            static_thumb_dir = os.path.join(BASE_DIR, "static", "thumbnails")
                            os.makedirs(static_thumb_dir, exist_ok=True)
                            
                            url_hash = hashlib.md5(video_stream_url.encode('utf-8')).hexdigest()
                            thumb_filename = f"thumb_{url_hash}.jpg"
                            thumb_filepath = os.path.join(static_thumb_dir, thumb_filename)
                            thumb_web_url = f"/static/thumbnails/{thumb_filename}"
                            
                            if os.path.exists(thumb_filepath):
                                thumbnail = thumb_web_url
                            else:
                                logger.info(f"Generating thumbnail for direct video {video_stream_url} via ffmpeg...")
                                static_ffmpeg.add_paths()
                                
                                headers_opt = []
                                http_headers = info.get("http_headers") or {}
                                
                                # Extract cookies from ydl or ydl_nocookies if present in local scope
                                cookie_list = []
                                ydl_obj = None
                                if "ydl" in locals() and locals()["ydl"]:
                                    ydl_obj = locals()["ydl"]
                                elif "ydl_nocookies" in locals() and locals()["ydl_nocookies"]:
                                    ydl_obj = locals()["ydl_nocookies"]
                                    
                                if ydl_obj and hasattr(ydl_obj, "cookiejar"):
                                    for cookie in ydl_obj.cookiejar:
                                        cookie_list.append(f"{cookie.name}={cookie.value}")
                                        
                                headers_dict = http_headers.copy()
                                if cookie_list:
                                    headers_dict["Cookie"] = "; ".join(cookie_list)
                                    
                                if headers_dict:
                                    headers_str = "".join(f"{k}: {v}\r\n" for k, v in headers_dict.items())
                                    headers_opt = ["-headers", headers_str]
                                    
                                res = subprocess.run([
                                    "ffmpeg",
                                    "-y",
                                    *headers_opt,
                                    "-i", video_stream_url,
                                    "-vf", "scale=640:-2",
                                    "-map", "0:v:0",
                                    "-vframes", "1",
                                    "-q:v", "4",
                                    thumb_filepath
                                ], capture_output=True, timeout=15)
                                
                                if res.returncode != 0 or not os.path.exists(thumb_filepath):
                                    logger.warning(f"ffmpeg scaled thumbnail generation failed (code {res.returncode}). Retrying without scale filter...")
                                    subprocess.run([
                                        "ffmpeg",
                                        "-y",
                                        *headers_opt,
                                        "-i", video_stream_url,
                                        "-map", "0:v:0",
                                        "-vframes", "1",
                                        "-q:v", "4",
                                        thumb_filepath
                                    ], capture_output=True, timeout=10)
                                if os.path.exists(thumb_filepath):
                                    thumbnail = thumb_web_url
                                    logger.info(f"Successfully generated thumbnail at {thumb_filepath}")
                        except Exception as e:
                            logger.warning(f"Failed to generate thumbnail for direct video: {e}")

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
                    if not is_direct_audio:
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
                                        
                                    acodec = f.get("acodec")
                                    has_audio = acodec and acodec != "none" and acodec != "unknown"
                                    
                                    if is_tiktok or has_audio:
                                        total_size = v_size
                                        fmt_id = f.get("format_id")
                                    else:
                                        total_size = (v_size + best_audio_size) if v_size else 0
                                        fmt_id = f"bestvideo[height={height}]+bestaudio[ext=m4a]/bestvideo[height={height}]+bestaudio/best[height={height}]"

                                    opt_dict = {
                                        "format_id": fmt_id,
                                        "resolution": res_label,
                                        "ext": "mp4",
                                        "type": "video",
                                        "size": format_size(total_size) if total_size else "Unknown Size",
                                        "label": f"Video {res_label}",
                                        "url": f.get("url")
                                    }
                                    if best_audio_format and best_audio_format.get("url"):
                                        opt_dict["audio_url"] = best_audio_format.get("url")
                                    video_options.append(opt_dict)
                                    added_resolutions.add(res_label)

                        video_options.sort(key=lambda x: int(x["resolution"].replace("p", "")), reverse=True)

                        # Resolve sizes of single video formats in parallel if they are Unknown Size or missing
                        is_twitter = "twitter.com" in url.lower() or "x.com" in url.lower()
                        is_tiktok = "tiktok.com" in url.lower()
                        is_instagram = "instagram.com" in url.lower()
                        is_reddit = "reddit.com" in url.lower() or "redd.it" in url.lower()
                        
                        if video_options and (is_twitter or is_tiktok or is_instagram or is_reddit):
                            from concurrent.futures import ThreadPoolExecutor
                            client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt") if client_id else None
                            
                            def resolve_single_format_size(opt):
                                if opt.get("size") == "Unknown Size" or not opt.get("size"):
                                    url_to_check = opt.get("url") or info.get("url")
                                    if opt.get("format_id"):
                                        for f in info.get("formats", []):
                                            if f.get("format_id") == opt.get("format_id") and f.get("url"):
                                                url_to_check = f.get("url")
                                                break
                                    if url_to_check and url_to_check.startswith("http"):
                                        s_bytes = get_url_content_length(url_to_check, cookies_file=client_cookies)
                                        if s_bytes:
                                            opt["size"] = format_size(s_bytes)
                                            
                            with ThreadPoolExecutor(max_workers=min(10, len(video_options))) as executor:
                                list(executor.map(resolve_single_format_size, video_options))

                        if not video_options:
                            best_url = info.get("url")
                            if not best_url and formats_list:
                                best_url = formats_list[-1].get("url") if formats_list else None
                            v_size = None
                            if is_direct_video and best_url:
                                s_bytes = get_url_content_length(best_url)
                                if s_bytes:
                                    v_size = format_size(s_bytes)
                            is_fallback_direct = best_url and best_url.startswith("http") and best_url != url
                            fmt_id = "direct_video" if is_fallback_direct else "bestvideo+bestaudio/best"
                            video_options.append({
                                "format_id": fmt_id,
                                "resolution": "Best",
                                "ext": "mp4",
                                "type": "video",
                                "size": v_size,
                                "label": "Video (Best Quality)",
                                "url": best_url
                            })

                    # --- Build audio options ---
                    est_m4a_size = format_size(best_audio_size) if best_audio_size else None
                    audio_url = None
                    if best_audio_format:
                        audio_url = best_audio_format.get("url")
                    if not audio_url:
                        for f in formats_list:
                            if f.get("acodec") != "none" and f.get("url"):
                                audio_url = f.get("url")
                                break
                    if not audio_url:
                        audio_url = info.get("url")
                    if not audio_url and formats_list:
                        audio_url = formats_list[-1].get("url")

                    audio_options.append({
                        "format_id": "bestaudio[ext=m4a]/bestaudio",
                        "resolution": "Audio",
                        "ext": "m4a",
                        "type": "audio",
                        "size": est_m4a_size,
                        "label": "M4A AAC (Original Quality - Fast)",
                        "url": audio_url
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
                            "label": f"MP3 {q_name} ({q_label})",
                            "url": audio_url
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
            elif "twitter" in extractor or "x.com" in url or "twitter.com" in url:
                platform_label = "Twitter/X"
                platform_class = "twitter-x"
            elif "reddit" in extractor or "reddit.com" in url or "redd.it" in url:
                platform_label = "Reddit"
                platform_class = "reddit"
            elif "soundcloud" in extractor or "soundcloud.com" in url:
                platform_label = "SoundCloud"
                platform_class = "soundcloud"
            elif "pinterest" in extractor or "pinterest.com" in url or "pin.it" in url:
                platform_label = "Pinterest"
                platform_class = "pinterest"
            elif "vimeo" in extractor or "vimeo.com" in url:
                platform_label = "Vimeo"
                platform_class = "vimeo"
            else:
                if is_direct_image:
                    platform_label = "Image File"
                elif is_direct_audio:
                    platform_label = "Audio File"
                elif is_direct_video:
                    platform_label = "Video File"
                else:
                    raw_platform = info.get("extractor_key") or info.get("extractor") or ""
                    if not raw_platform or raw_platform.lower() in ["generic", "html5mediaembed", "video", "default"]:
                        try:
                            from urllib.parse import urlparse
                            parsed_url = urlparse(url)
                            netloc = parsed_url.netloc.lower()
                            if netloc.startswith("www."):
                                netloc = netloc[4:]
                            if netloc:
                                platform_label = netloc.capitalize()
                            else:
                                platform_label = "Web Video"
                        except Exception:
                            platform_label = "Web Video"
                    else:
                        platform_label = raw_platform.capitalize()
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

            # Resolve sizes of TikTok video_options in parallel
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

            # Post-process video_options to ensure correct type based on extension or URL path
            for opt in video_options:
                ext = (opt.get("ext") or "").lower()
                url_path = (opt.get("url") or "").lower()
                
                # If extension is not specified, guess it from the URL path/query
                if not ext and url_path:
                    try:
                        parsed_path = urllib.parse.urlparse(url_path).path.lower()
                        for known_ext in [".mp4", ".m3u8", ".mp3", ".m4a", ".jpg", ".jpeg", ".png", ".webp", ".gif", ".html", ".htm"]:
                            if parsed_path.endswith(known_ext) or f"{known_ext}?" in url_path or f"{known_ext}/" in url_path:
                                ext = known_ext.lstrip(".")
                                opt["ext"] = ext
                                break
                    except Exception as parse_err:
                        logger.warning(f"Error parsing option URL in post-process: {parse_err}")
                
                # Ensure the 'type' field is correct based on the extension
                if ext in ["html", "htm"]:
                    opt["type"] = "webpage"
                elif ext in ["jpg", "jpeg", "png", "webp", "gif"]:
                    opt["type"] = "image"
                elif ext in ["mp3", "m4a", "wav", "ogg", "aac", "flac", "opus"]:
                    opt["type"] = "audio"
                elif ext in ["mp4", "mkv", "avi", "mov", "flv", "webm", "m3u8", "ts"]:
                    opt["type"] = "video"
                
                # Extra check for resolution keywords or labels if type is still not set or is generic
                if not opt.get("type") or opt.get("type") == "video":
                    res_lower = (opt.get("resolution") or "").lower()
                    label_lower = (opt.get("label") or "").lower()
                    if "webpage" in res_lower or "webpage" in label_lower or "html" in label_lower:
                        opt["type"] = "webpage"
                    elif "image" in label_lower or "photo" in label_lower:
                        opt["type"] = "image"
                    elif "audio" in label_lower or "sound" in label_lower:
                        opt["type"] = "audio"
                    elif not opt.get("type"):
                        opt["type"] = "video"

            return jsonify({
                "status": "success",
                "title": title,
                "uploader": uploader,
                "duration": duration,
                "duration_raw": duration_sec,
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
        return jsonify({"status": "error", "message": f"Could not parse URL. {strip_ansi_codes(str(e))}"}), 500


@info_bp.route("/api/video/analyze-scenes", methods=["GET"])
def analyze_video_scenes():
    video_url = request.args.get("url")
    if not video_url:
        return jsonify({"status": "error", "message": "Missing url parameter"}), 400
        
    try:
        referer = get_referer_by_url(video_url)
        headers_str = (
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\r\n"
            f"Referer: {referer}\r\n"
        )
        
        # Run ffmpeg with showinfo filter to detect visual scene changes
        cmd = [
            "ffmpeg",
            "-headers", headers_str,
            "-ss", "0",
            "-t", "600",  # Scan first 10 minutes maximum to keep it extremely fast
            "-i", video_url,
            "-vf", "select='gt(scene,0.45)',showinfo",
            "-f", "null",
            "-"
        ]
        
        # Limit running time to 12 seconds to avoid blocking thread
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=12
            )
            stderr_output = result.stderr or ""
        except subprocess.TimeoutExpired as te:
            stderr_output = te.stderr or ""
            
        # Parse showinfo output for pts_time values
        # e.g., "pts_time:12.3456"
        matches = re.findall(r"pts_time:\s*([0-9.]+)", stderr_output)
        timestamps = sorted(list(set(round(float(m)) for m in matches)))
        
        return jsonify({
            "status": "success",
            "scenes": timestamps
        })
    except Exception as e:
        logger.error(f"Error in analyze_video_scenes: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    