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

from config import TEMP_DOWNLOAD_DIR
from utils.helpers import format_duration, format_size, get_referer_by_url, get_url_content_length
from utils.ytdl import create_ydl_instance

from extractors import (
    extract_instagram_via_gallery_dl,
    extract_tiktok_slideshow_via_gallery_dl,
    extract_twitter_via_gallery_dl,
    extract_reddit_via_gallery_dl,
    scrape_reddit_fallback,
    parse_threads_page,
    extract_pinterest_via_gallery_dl,
    scrape_fb_post
)

info_bp = Blueprint("info", __name__)
logger = logging.getLogger(__name__)


def strip_ansi_codes(text):
    if not text:
        return ""
    # Strip ANSI color/escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def resolve_hls_size(m3u8_url, referer=None):
    try:
        import requests
        from urllib.parse import urljoin
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if referer:
            headers["Referer"] = referer
            
        resp = requests.get(m3u8_url, headers=headers, verify=False, timeout=5)
        if resp.status_code != 200:
            return None
            
        content = resp.text
        if "#EXT-X-STREAM-INF" in content:
            # Variant redirect
            variants = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
            if variants:
                variant_url = variants[0]
                if not variant_url.startswith("http"):
                    variant_url = urljoin(m3u8_url, variant_url)
                return resolve_hls_size(variant_url, referer)
                
        segments = []
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                segments.append(line)
                
        if not segments:
            return None
            
        total_segments = len(segments)
        mid_idx = total_segments // 2
        target_segment = segments[mid_idx]
        if not target_segment.startswith("http"):
            target_segment = urljoin(m3u8_url, target_segment)
            
        seg_resp = requests.head(target_segment, headers=headers, verify=False, timeout=5)
        content_len = seg_resp.headers.get("Content-Length")
        # If HEAD returned no Content-Length or a dummy/tiny content length (e.g. < 1000 bytes), fall back to GET
        if not content_len or int(content_len) < 1000:
            seg_resp = requests.get(target_segment, headers=headers, verify=False, stream=True, timeout=5)
            content_len = seg_resp.headers.get("Content-Length")
            
        if content_len:
            return int(content_len) * total_segments
    except Exception:
        pass
    return None


def generic_html_link_harvester(url, client_id):
    try:
        import requests as req
        from urllib.parse import urlparse
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # Fetch raw HTML
        resp = req.get(url, headers=headers, verify=False, timeout=12)
        if resp.status_code != 200:
            return None
        html = resp.text
        
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Get page path segments
        path_segments = [seg for seg in parsed_url.path.split('/') if seg]
        last_segment = path_segments[-1] if path_segments else ""
        
        # Extract Title
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else "Web Video"
        
        # Extract Thumbnail
        thumb_match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE) or \
                      re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html, re.IGNORECASE)
        thumbnail = thumb_match.group(1).strip() if thumb_match else ""
        
        # Extract Description
        desc_match = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE) or \
                     re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        description = desc_match.group(1).strip() if desc_match else ""
        
        # Clean up backslashes
        clean_html = html.replace('\\/', '/').replace('\\', '')
        
        # Try to extract current movie's ID to filter out recommended movies in sidebars
        main_movie_id = ""
        movie_match = re.search(r'"movie"\s*:\s*\{\s*"id"\s*:\s*"(\d+)"', clean_html)
        if movie_match:
            main_movie_id = movie_match.group(1)
        if not main_movie_id:
            movie_match = re.search(r'"movieId"\s*:\s*"([a-zA-Z0-9_-]+)"', clean_html)
            if movie_match:
                main_movie_id = movie_match.group(1)
        if not main_movie_id:
            movie_match = re.search(r'"postId"\s*:\s*(\d+)', clean_html)
            if movie_match:
                main_movie_id = movie_match.group(1)

        # Find all episodes / links via JSON structures
        episode_pattern = r'\{[^{}]*"server"[^{}]*"name"[^{}]*"slug"[^{}]*"link"[^{}]*\}'
        ep_matches = re.findall(episode_pattern, clean_html)
        
        video_options = []
        all_parsed_options = []
        seen_urls = set()
        
        def get_digits(text):
            digits = "".join(re.findall(r'\d+', text))
            return int(digits) if digits else None
            
        last_val = get_digits(last_segment)
        
        # 1. Match against episode list objects
        for ep_str in ep_matches:
            try:
                if not ep_str.startswith('{'): ep_str = '{' + ep_str
                if not ep_str.endswith('}'): ep_str = ep_str + '}'
                
                # Filter by movie_id if we have parsed the main movie ID
                movie_id_match = re.search(r'"movie_id"\s*:\s*"([^"]+)"', ep_str)
                if movie_id_match and main_movie_id:
                    if movie_id_match.group(1) != main_movie_id:
                        continue
                
                server = re.search(r'"server"\s*:\s*"([^"]+)"', ep_str)
                name = re.search(r'"name"\s*:\s*"([^"]+)"', ep_str)
                slug = re.search(r'"slug"\s*:\s*"([^"]+)"', ep_str)
                link = re.search(r'"link"\s*:\s*"([^"]+)"', ep_str)
                type_match = re.search(r'"type"\s*:\s*"([^"]+)"', ep_str)
                
                if link:
                    media_url = link.group(1)
                    if media_url.startswith('/'):
                        if 'fcloud.live' in clean_html:
                            media_url = 'https://fcloud.live' + media_url
                        else:
                            media_url = f"https://{domain}" + media_url

                    slug_val = slug.group(1) if slug else ""
                    name_val = name.group(1) if name else ""
                    server_val = server.group(1) if server else "Server"
                    
                    is_match = False
                    if last_segment:
                        if last_segment.lower() == slug_val.lower():
                            is_match = True
                        else:
                            name_val_digits = get_digits(name_val)
                            slug_val_digits = get_digits(slug_val)
                            if last_val is not None:
                                if last_val == name_val_digits or last_val == slug_val_digits:
                                    is_match = True
                                    
                    is_stream = (media_url.endswith('.m3u8') or '.m3u8' in media_url or 
                                 media_url.endswith('.mp4') or '/player/master/' in media_url)
                    if is_stream:
                        type_val = type_match.group(1) if type_match else ""
                        type_suffix = f" [{type_val.upper()}]" if type_val else ""
                        option_obj = {
                            "format_id": "",
                            "resolution": "Auto Stream",
                            "ext": "mp4",
                            "type": "video",
                            "size": "Unknown Size",
                            "label": f"Server: {server_val}{type_suffix} (Episode {name_val})",
                            "episode": name_val,
                            "server": f"Server: {server_val}{type_suffix}",
                            "url": media_url
                        }
                        if is_match:
                            seen_urls.add(media_url)
                            option_obj["format_id"] = f"direct_video_{len(video_options)+1}"
                            video_options.append(option_obj)
                        else:
                            all_parsed_options.append(option_obj)
            except Exception:
                pass
                
        # 2. Fallback: If no matched episodes found, but we did find some parsed options (e.g. overview page)
        if not video_options and all_parsed_options:
            for opt in all_parsed_options:
                if opt["url"] not in seen_urls:
                    seen_urls.add(opt["url"])
                    opt["format_id"] = f"direct_video_{len(video_options)+1}"
                    video_options.append(opt)
                    
        # 3. Second Fallback: If still no options found, search page for any raw .m3u8 or .mp4 links
        if not video_options:
            raw_m3u8_links = re.findall(r'https?://[^\s"\'\\<>#]+\.(?:m3u8|mp4)[^\s"\'\\<>#]*', clean_html)
            for link in raw_m3u8_links:
                link = link.rstrip('\\').rstrip('"').rstrip("'")
                if link not in seen_urls:
                    seen_urls.add(link)
                    video_options.append({
                        "format_id": f"direct_video_{len(video_options)+1}",
                        "resolution": "Auto Stream",
                        "ext": "mp4",
                        "type": "video",
                        "size": "Unknown Size",
                        "label": f"Direct Link #{len(video_options)+1}",
                        "url": link
                    })
                    
        if not video_options:
            return None
            
        # Resolve HLS / Direct CDN stream sizes in parallel
        if video_options:
            from concurrent.futures import ThreadPoolExecutor
            
            def resolve_opt_size(opt):
                opt_url = opt.get("url")
                if not opt_url:
                    return
                try:
                    # Resolve direct media URL inside embed player parameters if any
                    actual_url = opt_url
                    from urllib.parse import parse_qs, urlparse
                    parsed = urlparse(opt_url)
                    queries = parse_qs(parsed.query)
                    for val_list in queries.values():
                        for val in val_list:
                            if val.startswith("http") and (".m3u8" in val or ".mp4" in val):
                                actual_url = val
                                break

                    if actual_url.endswith('.m3u8') or '.m3u8' in actual_url or '/player/master/' in actual_url:
                        size_bytes = resolve_hls_size(actual_url, url)
                    else:
                        size_bytes = get_url_content_length(actual_url)
                        
                    if size_bytes and size_bytes >= 1024 * 1024:  # Ignore sizes < 1MB (e.g. ad trackers or tiny placeholders)
                        opt["size"] = format_size(size_bytes)
                except Exception:
                    pass
                    
            with ThreadPoolExecutor(max_workers=min(15, len(video_options))) as executor:
                list(executor.map(resolve_opt_size, video_options))
            
        return {
            "status": "success",
            "title": title,
            "uploader": domain,
            "duration": "Unknown",
            "duration_raw": 0,
            "thumbnail": thumbnail,
            "is_shorts": False,
            "platform_label": domain.capitalize(),
            "platform_class": "default",
            "views": "—",
            "likes": "—",
            "upload_date": "—",
            "description": description,
            "category": "Web Video",
            "tags": [],
            "video_options": video_options,
            "audio_options": [],
            "subtitles": {},
            "images": [{"label": "Thumbnail", "url": thumbnail, "ext": "jpg"}] if thumbnail else [],
        }
    except Exception as err:
        logger.warning(f"generic_html_link_harvester failed: {err}")
        return None


@info_bp.route("/api/info", methods=["POST"])
def get_info():
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    if "tiktok.com" in url.lower() and "/photo/" in url.lower():
        url = re.sub(r'/photo/', '/video/', url, flags=re.IGNORECASE)
    client_id = data.get("client_id")

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
                    "message": "Bài đăng Twitter/X này yêu cầu cookie tài khoản để truy cập hoặc bị giới hạn độ tuổi. Vui lòng đăng nhập vào Twitter/X trên trình duyệt, xuất và tải lên file cookie J2TEAM (chọn định dạng Netscape hoặc JSON) để tiếp tục."
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
                "duration_raw": 15 if unique_video_urls else 5,
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
        # For video-specific URLs, prefer yt-dlp (better HD + metadata support)
        # Custom scraper is primarily for photo posts which yt-dlp cannot handle
        is_fb_video_url = any(p in url.lower() for p in ["/share/v/", "/videos/", "/reel/", "/watch", "fb.watch"])
        
        if not is_fb_video_url:
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
        "extractor_args": {
            "youtube": {
                "player_client": ["default"],
            }
        },
    }
    if ImpersonateTarget:
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
                
                is_facebook = any(domain in url.lower() for domain in ["facebook.com", "fb.com", "fb.watch", "fb.gg"])
                if is_facebook:
                    # Try custom scraper as last resort before returning error
                    try:
                        logger.info("yt-dlp failed for Facebook. Trying custom scraper as fallback...")
                        fb_fallback = scrape_fb_post(url, client_id)
                        if fb_fallback and fb_fallback.get("status") == "success" and (fb_fallback.get("images") or fb_fallback.get("video_options")):
                            video_options = fb_fallback.get("video_options", [])
                            if video_options:
                                from concurrent.futures import ThreadPoolExecutor
                                client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt") if client_id else None
                                def resolve_fb_fallback_size(opt):
                                    url_to_check = opt.get("url")
                                    if url_to_check:
                                        s_bytes = get_url_content_length(url_to_check, cookies_file=client_cookies)
                                        if s_bytes:
                                            opt["size"] = format_size(s_bytes)
                                with ThreadPoolExecutor(max_workers=min(10, len(video_options))) as executor:
                                    list(executor.map(resolve_fb_fallback_size, video_options))
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
                            "message": "Reddit yêu cầu cookie tài khoản để truy cập hoặc IP hệ thống đang bị rate-limit. Vui lòng đăng nhập vào Reddit trên trình duyệt, xuất và tải lên file cookie J2TEAM (chọn định dạng Netscape hoặc JSON) của Reddit để tiếp tục."
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
                if is_reddit and reddit_gallery_fallback:
                    logger.info("yt-dlp failed for Reddit video. Falling back to pre-extracted gallery-dl info.")
                    return jsonify(reddit_gallery_fallback)
                if is_twitter and twitter_gallery_fallback:
                    logger.info("yt-dlp failed for Twitter video. Falling back to pre-extracted gallery-dl info.")
                    return jsonify(twitter_gallery_fallback)
                if is_pinterest and pinterest_gallery_fallback:
                    logger.info("yt-dlp failed for Pinterest video. Falling back to pre-extracted gallery-dl info.")
                    return jsonify(pinterest_gallery_fallback)
                harvester_info = generic_html_link_harvester(url, client_id)
                if harvester_info:
                    logger.info(f"Generic HTML link harvester succeeded for {url} (nocookie_e). Found {len(harvester_info.get('video_options', []))} options.")
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
                            "message": "Instagram yêu cầu cookie tài khoản để truy cập. Vui lòng xuất và tải lên file cookie J2TEAM (chọn định dạng Netscape hoặc JSON) để tiếp tục."
                        }), 400
                return jsonify({
                    "status": "error",
                    "message": "Instagram yêu cầu cookie tài khoản để truy cập. Vui lòng xuất và tải lên file cookie J2TEAM (chọn định dạng Netscape hoặc JSON) để tiếp tục."
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
            harvester_info = generic_html_link_harvester(url, client_id)
            if harvester_info:
                logger.info(f"Generic HTML link harvester succeeded for {url} (not info). Found {len(harvester_info.get('video_options', []))} options.")
                return jsonify(harvester_info)
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
                    video_options.append({
                        "format_id": "bestvideo+bestaudio/best",
                        "resolution": "Best",
                        "ext": "mp4",
                        "type": "video",
                        "size": None,
                        "label": "Video (Best Quality)",
                        "url": best_url
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
                                "label": f"Video {res_label}",
                                "url": f.get("url")
                            }
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
                    video_options.append({
                        "format_id": "bestvideo+bestaudio/best",
                        "resolution": "Best",
                        "ext": "mp4",
                        "type": "video",
                        "size": None,
                        "label": "Video (Best Quality)",
                        "url": best_url
                    })

                # --- Build audio options ---
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
