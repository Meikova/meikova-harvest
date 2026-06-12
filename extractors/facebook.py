import os
import json
import re
import logging
import urllib.parse
import html as html_lib
import requests

from config import TEMP_DOWNLOAD_DIR
from utils.helpers import get_url_content_length, format_size

logger = logging.getLogger(__name__)

def scrape_fb_post(url, client_id=None):
    cookies_dir = os.path.join(TEMP_DOWNLOAD_DIR, "cookies")
    cookie_file = os.path.join(cookies_dir, f"cookies_{client_id}.txt") if client_id else None
    
    def fetch_facebook_html(use_cookies):
        command = [
            "curl",
            "-s",
            "-L",
            "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "-H", "Accept-Language: vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "-H", "Sec-Fetch-Mode: navigate",
            "-H", "Upgrade-Insecure-Requests: 1",
        ]
        if use_cookies and cookie_file and os.path.exists(cookie_file):
            command.extend(["-b", cookie_file])
            logger.info("Using client cookies for custom Facebook scraping via curl.")
        else:
            logger.info("Not using cookies for custom Facebook scraping via curl.")
            
        command.append(url)
        
        try:
            import subprocess
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
            if len(result.stdout) > 0:
                return result.stdout
        except Exception as e:
            logger.warning(f"Failed to fetch Facebook page via curl (use_cookies={use_cookies}): {e}")
        return None

    # Step 1: Try WITHOUT cookies first to get the clean public post page without cookie-induced feed noise
    html = fetch_facebook_html(use_cookies=False)
    
    def parse_html_content(html_content):
        if not html_content:
            return None
            
        # Detect Facebook security checkpoint / captcha / login redirection
        html_lower = html_content.lower()
        is_blocked = False
        
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE)
        page_title = ""
        if title_match:
            page_title = title_match.group(1).strip()
            page_title_lower = page_title.lower()
            if (any(kw in page_title_lower for kw in ["đăng nhập", "security check", "checkpoint", "log in to facebook", "login to facebook"])
                or page_title_lower in ["login", "log in"]):
                is_blocked = True
                logger.warning(f"Facebook custom scraping blocked by title: {page_title}")
                
        if not is_blocked and len(html_content) < 200000:
            for keyword in ["checkpoint", "captcha", "login_form", "login.php", "security check"]:
                if keyword in html_lower:
                    is_blocked = True
                    logger.warning(f"Facebook custom scraping blocked by keyword: {keyword}")
                    break
        
        if is_blocked:
            return {"status": "blocked"}
            
        # Extract Title and Description from Meta tags
        title = ""
        desc_match = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', html_content) or re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html_content)
        if desc_match:
            title = desc_match.group(1)
            title = html_lib.unescape(title)
            
        title_match = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html_content)
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
        thumb_match = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html_content)
        if thumb_match:
            thumbnail = html_lib.unescape(thumb_match.group(1))
            
        # Extract canonical URL or og:url
        canonical_match = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', html_content) or re.search(r'<meta\s+property="og:url"\s+content="([^"]+)"', html_content)
        canonical_url = canonical_match.group(1) if canonical_match else url
        
        # Extract post ID for targeted filtering
        post_id = None
        for target_url in [canonical_url, url]:
            if post_id:
                break
            m = re.search(r'/posts/([^/?#]+)', target_url)
            if m:
                post_id = m.group(1)
                continue
            m = re.search(r'story_fbid=([^&#]+)', target_url)
            if m:
                post_id = m.group(1)
                continue
            m = re.search(r'[?&]fbid=([^&#]+)', target_url)
            if m:
                post_id = m.group(1)
                continue
            m = re.search(r'/photos/[^/]+/([^/?#]+)', target_url)
            if m:
                post_id = m.group(1)
                continue
            m = re.search(r'/reel/([^/?#]+)', target_url)
            if m:
                post_id = m.group(1)
                continue
            m = re.search(r'[?&]v=([^&#]+)', target_url)
            if m:
                post_id = m.group(1)
                continue
            m = re.search(r'/videos/([^/?#]+)', target_url)
            if m:
                post_id = m.group(1)
                continue
            m = re.search(r'/permalink/(\d+)', target_url)
            if m:
                post_id = m.group(1)
                continue
            m = re.search(r'/stories/(\d+)/([^/?#]+)', target_url)
            if m:
                bucket_id = m.group(1)
                story_id_raw = m.group(2)
                try:
                    import base64
                    padding = '=' * (4 - len(story_id_raw) % 4)
                    decoded_bytes = base64.b64decode(story_id_raw + padding)
                    decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
                    num_match = re.search(r'(\d{10,})', decoded_str)
                    if num_match:
                        post_id = num_match.group(1)
                        logger.info(f"Resolved story post ID from base64: {post_id}")
                    else:
                        post_id = story_id_raw
                except Exception as story_err:
                    logger.warning(f"Could not decode story base64 ID: {story_err}")
                    post_id = story_id_raw
                continue
        
        # Fallback: for /share/v/, /share/p/, /share/r/, or raw /share/ URLs, resolve via share token
        if not post_id:
            share_token = None
            share_match = re.search(r'/share/([vpr]/)?([^/?#]+)', url)
            if share_match:
                share_token = share_match.group(2)
            
            if share_token:
                script_blocks = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html_content, re.DOTALL)
                for script_text in script_blocks:
                    if share_token in script_text:
                        decoded_script = script_text.replace("\\/", "/").replace("\\u00253A", ":").replace("\\u00252F", "/").replace("\\u0025", "%")
                        decoded_script = urllib.parse.unquote(decoded_script)
                        urls_in_script = re.findall(r'"url"\s*:\s*"([^"]+)"', decoded_script)
                        for decoded_url in urls_in_script:
                            m = re.search(r'/posts/([^/?#]+)', decoded_url)
                            if m:
                                post_id = m.group(1)
                                logger.info(f"Resolved share URL to posts ID via share token: {post_id}")
                                break
                            m = re.search(r'/permalink/([^/?#]+)', decoded_url)
                            if m:
                                post_id = m.group(1)
                                logger.info(f"Resolved share URL to permalink ID via share token: {post_id}")
                                break
                            m = re.search(r'/photos/[^/]+/([^/?#]+)', decoded_url)
                            if m:
                                post_id = m.group(1)
                                logger.info(f"Resolved share URL to photos ID via share token: {post_id}")
                                break
                            m = re.search(r'/videos/([^/?#]+)', decoded_url)
                            if m:
                                post_id = m.group(1)
                                logger.info(f"Resolved share URL to videos ID via share token: {post_id}")
                                break
                        if post_id:
                            break
            
        # Last resort: scan entire HTML for post ID patterns in URLs and select the most frequent one
        if not post_id:
            decoded_html = html_content.replace("\\/", "/")
            post_matches = re.findall(r'/posts/(\d{10,})', decoded_html)
            perm_matches = re.findall(r'/permalink/(\d{10,})', decoded_html)
            vid_matches = re.findall(r'/videos/(\d{10,})', decoded_html)
            photo_matches = re.findall(r'/photos/[^/]+/(\d{10,})', decoded_html)
            
            all_id_matches = post_matches + perm_matches + vid_matches + photo_matches
            if all_id_matches:
                from collections import Counter
                id_counts = Counter(all_id_matches)
                post_id = id_counts.most_common(1)[0][0]
                logger.info(f"Resolved post ID from HTML URL patterns (last resort): {post_id}")
            else:
                post_id_matches = re.findall(r'"post_id"\s*:\s*"(\d{10,})"', html_content)
                if post_id_matches:
                    from collections import Counter
                    post_id_counts = Counter(post_id_matches)
                    post_id = post_id_counts.most_common(1)[0][0]
                    logger.info(f"Resolved post ID from JSON data (last resort): {post_id}")
                    
        return {
            "status": "success",
            "html": html_content,
            "post_id": post_id,
            "title": title,
            "uploader": uploader,
            "thumbnail": thumbnail,
            "canonical_url": canonical_url
        }

    parsed = parse_html_content(html)
    
    # If the non-cookie request failed, got blocked, or failed to resolve a target post ID,
    # retry WITH cookies to scrape private group/restricted content.
    if (not parsed or parsed.get("status") == "blocked" or not parsed.get("post_id")) and cookie_file and os.path.exists(cookie_file):
        logger.info("Facebook scraping without cookies failed, was blocked, or yielded no post ID. Retrying WITH cookies...")
        html = fetch_facebook_html(use_cookies=True)
        parsed = parse_html_content(html)
        
    if not parsed:
        return {"status": "error", "message": "Facebook returned empty response or curl failed"}
        
    if parsed.get("status") == "blocked":
        return {
            "status": "error",
            "message": "Facebook security checkpoint or login wall triggered. Account cookies may be invalid, expired, or flagged."
        }
        
    html = parsed["html"]
    post_id = parsed["post_id"]
    title = parsed["title"]
    uploader = parsed["uploader"]
    thumbnail = parsed["thumbnail"]
    canonical_url = parsed["canonical_url"]
    
    logger.info(f"Extracted Facebook post/media ID: {post_id}")
    
    # Check if there is an album/collection ID associated with the post
    # Skip album detection for video-specific URLs
    is_video_url = any(pattern in url.lower() for pattern in ["/share/v/", "/share/r/", "/videos/", "/reel/", "/reels/", "/watch", "fb.watch"])
    album_id = None
    if not is_video_url:
        pcb_match = re.search(r'set=pcb\.(\d+)', html)
        if pcb_match:
            album_id = f"pcb.{pcb_match.group(1)}"
        else:
            a_match = re.search(r'set=a\.(\d+)', html)
            if a_match:
                album_id = f"a.{a_match.group(1)}"
            
    album_html = None
    if album_id:
        album_url = f"https://www.facebook.com/media/set/?set={album_id}"
        logger.info(f"Multi-photo album detected. Fetching album page: {album_url}")
        
        album_command = [
            "curl",
            "-s",
            "-L",
            "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "-H", "Accept-Language: vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "-H", "Sec-Fetch-Mode: navigate",
            "-H", "Upgrade-Insecure-Requests: 1",
        ]
        if cookie_file and os.path.exists(cookie_file):
            album_command.extend(["-b", cookie_file])
        album_command.append(album_url)
        
        try:
            import subprocess
            album_result = subprocess.run(album_command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
            if album_result.returncode == 0 and album_result.stdout:
                album_html = album_result.stdout
                logger.info(f"Successfully fetched album page (length={len(album_html)})")
        except Exception as album_err:
            logger.warning(f"Failed to fetch album page: {album_err}")
        
    # Find all application/json script blocks
    scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
    album_scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', album_html, re.DOTALL) if album_html else []
    
    video_options = []
    images = []
    added_image_filenames = set()
    added_video_urls = set()
    
    def extract_filename(url_str):
        try:
            path = urllib.parse.urlparse(url_str).path
            return os.path.basename(path)
        except:
            return url_str

    def is_valid_photo(uri):
        if not uri or not isinstance(uri, str):
            return False
        # Filter out UI assets, stickers, reactions, emojis, tracking pixels, and profile photos
        if any(x in uri.lower() for x in ["/rsrc.php/", "/emoji.php/", "/assets/", "pixel", "/emoji/", "/static/", "/t39.30808-1/", "/t39.1997-"]):
            return False
        # Filter out small thumbnails or icons
        if any(x in uri.lower() for x in ["_s.jpg", "_t.jpg", "/p50x50/", "/p100x100/", "/p150x150/"]):
            return False
        return True
    
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
                                    if is_valid_photo(uri):
                                        filename = extract_filename(uri)
                                        if filename not in added_image_filenames:
                                            added_image_filenames.add(filename)
                                            images.append({
                                                "label": f"Photo {len(images)+1}",
                                                "url": uri,
                                                "ext": "jpg"
                                            })
            
            # Check for direct Photo types or generic image nodes
            v_img = d.get("viewer_image")
            if isinstance(v_img, dict) and v_img.get("uri"):
                uri = v_img["uri"].replace("\\/", "/").replace("\\u0025", "%")
                uri = urllib.parse.unquote(uri)
                if is_valid_photo(uri):
                    filename = extract_filename(uri)
                    if filename not in added_image_filenames:
                        added_image_filenames.add(filename)
                        images.append({
                            "label": f"Photo {len(images)+1}",
                            "url": uri,
                            "ext": "jpg"
                        })
            
            img = d.get("image")
            if isinstance(img, dict) and img.get("uri"):
                uri = img["uri"].replace("\\/", "/").replace("\\u0025", "%")
                uri = urllib.parse.unquote(uri)
                if any(x in uri.lower() for x in ["fbcdn.net", "scontent"]):
                    if is_valid_photo(uri):
                        filename = extract_filename(uri)
                        if filename not in added_image_filenames:
                            added_image_filenames.add(filename)
                            images.append({
                                "label": f"Photo {len(images)+1}",
                                "url": uri,
                                "ext": "jpg"
                            })
                            
            # Check for Video options (playable_url, progressive_url, and HD variants)
            video_url_fields = [
                ("playable_url_quality_hd", "HD"),
                ("browser_native_hd_url", "HD"),
                ("playable_url", None),
                ("progressive_url", None),
                ("browser_native_sd_url", "SD"),
            ]
            for field_name, forced_res in video_url_fields:
                field_val = d.get(field_name)
                if field_val and isinstance(field_val, str) and "fbcdn.net" in field_val:
                    decoded_url = field_val.replace("\\/", "/").replace("\\u0025", "%")
                    decoded_url = urllib.parse.unquote(decoded_url)
                    
                    # Avoid dash/low quality chunks
                    if any(x in decoded_url.lower() for x in ["dash_baseline", "_nc_vs", "dash_prefetch"]):
                        continue
                    
                    if forced_res:
                        res = forced_res
                    else:
                        res = "HD" if any(kw in decoded_url.lower() for kw in ["quality_hd", "_hd.", "hd_src"]) else "SD"
                    
                    label = f"Facebook Video ({res})"
                    opt = {
                        "format_id": f"direct_video_{len(video_options)+1}",
                        "ext": "mp4",
                        "resolution": res,
                        "size": "Unknown Size",
                        "label": label,
                        "url": decoded_url
                    }
                    if decoded_url not in added_video_urls:
                        added_video_urls.add(decoded_url)
                        video_options.append(opt)
                            
            for v in d.values():
                if isinstance(v, (dict, list)):
                    search_graphql(v)
        elif isinstance(d, list):
            for item in d:
                if isinstance(item, (dict, list)):
                    search_graphql(item)
                    
    # Locate dictionaries that belong to the target story/post node
    target_nodes = []
    def locate_target_nodes(d):
        if isinstance(d, dict):
            is_target = False
            if post_id:
                # Direct match: post_id field equals our target
                if d.get("post_id") == post_id or d.get("id") == post_id:
                    is_target = True
                else:
                    for k, v in d.items():
                        if isinstance(v, str) and post_id in v:
                            if k in ["wwwURL", "url", "share_link", "permalink_url", "post_id"] or "story" in k or "node" in k:
                                is_target = True
                                break
            if is_target:
                target_nodes.append(d)
            else:
                for v in d.values():
                    if isinstance(v, (dict, list)):
                        locate_target_nodes(v)
        elif isinstance(d, list):
            for item in d:
                locate_target_nodes(item)
                
    # Parse scripts into memory
    parsed_main_scripts = []
    for script_text in scripts:
        try:
            data = json.loads(script_text)
            parsed_main_scripts.append(data)
        except:
            pass
            
    # Recursively search for reaction counts (likes)
    likes_val = None
    shares_val = None
    
    def find_reaction_counts(d, depth=0):
        nonlocal likes_val, shares_val
        if depth > 50:
            return
        if isinstance(d, dict):
            # Avoid comment likes (usually comment nodes have body, replies_fields, or author)
            is_comment = "body" in d or "replies_fields" in d or "author" in d
            
            if not is_comment:
                rc = d.get("reaction_count") or d.get("reactors")
                if isinstance(rc, dict) and isinstance(rc.get("count"), int):
                    val = rc["count"]
                    if val > 0 and (likes_val is None or (isinstance(likes_val, int) and val > likes_val) or isinstance(likes_val, str)):
                        likes_val = val
                elif isinstance(rc, int):
                    val = rc
                    if val > 0 and (likes_val is None or (isinstance(likes_val, int) and val > likes_val) or isinstance(likes_val, str)):
                        likes_val = val
                
                i18n = d.get("i18n_reaction_count")
                if i18n and isinstance(i18n, str):
                    if likes_val is None:
                        likes_val = i18n
                        
                sc = d.get("share_count")
                if isinstance(sc, dict) and isinstance(sc.get("count"), int):
                    shares_val = sc["count"]
                
            for v in d.values():
                if isinstance(v, (dict, list)):
                    find_reaction_counts(v, depth+1)
        elif isinstance(d, list):
            for item in d:
                if isinstance(item, (dict, list)):
                    find_reaction_counts(item, depth+1)

    # Scan reaction counts globally from all scripts first to ensure deep nodes are traversed
    for data in parsed_main_scripts:
        find_reaction_counts(data)

    # Try targeted extraction first
    targeted_success = False
    if post_id:
        for data in parsed_main_scripts:
            locate_target_nodes(data)
            
        if target_nodes:
            logger.info(f"Targeted story matching post ID '{post_id}' found. Extracting only target media.")
            for node in target_nodes:
                search_graphql(node)
            if images or video_options:
                targeted_success = True
                
    # Fallback to scanning everything if targeted extraction yielded no results
    if not targeted_success:
        logger.info("Targeted extraction yielded no results. Falling back to global scanning.")
        images = []
        video_options = []
        added_image_filenames = set()
        added_video_urls = set()
        for data in parsed_main_scripts:
            search_graphql(data)
    
    # Extract metadata from GraphQL data when og: tags are missing (logged-in pages)
    def extract_graphql_metadata(node):
        meta = {"uploader": None, "title": None, "thumbnail": None}
        if not isinstance(node, dict):
            return meta
        # Actor name (uploader)
        actors = node.get("actors", [])
        if isinstance(actors, list):
            for actor in actors:
                if isinstance(actor, dict) and actor.get("name"):
                    meta["uploader"] = actor["name"]
                    break
        # Message text (title/description)
        msg = node.get("message")
        if isinstance(msg, dict) and msg.get("text"):
            meta["title"] = msg["text"]
        # Fallback: check comet_sections for message
        if not meta["title"]:
            cs = node.get("comet_sections")
            if isinstance(cs, dict):
                def find_message_text(d, depth=0):
                    if depth > 10:
                        return None
                    if isinstance(d, dict):
                        if d.get("__typename") == "TextWithEntities" and d.get("text"):
                            return d["text"]
                        for v in d.values():
                            if isinstance(v, (dict, list)):
                                r = find_message_text(v, depth+1)
                                if r:
                                    return r
                    elif isinstance(d, list):
                        for item in d:
                            if isinstance(item, (dict, list)):
                                r = find_message_text(item, depth+1)
                                if r:
                                    return r
                    return None
                meta["title"] = find_message_text(cs)
        # Thumbnail from video node
        def find_thumbnail(d, depth=0):
            if depth > 10:
                return None
            if isinstance(d, dict):
                # preferred_thumbnail or thumbnailImage
                for tk in ["preferred_thumbnail", "thumbnailImage", "thumbnail_image"]:
                    thumb = d.get(tk)
                    if isinstance(thumb, dict) and thumb.get("uri"):
                        return thumb["uri"].replace("\\/", "/")
                    if isinstance(thumb, dict) and thumb.get("image"):
                        img = thumb["image"]
                        if isinstance(img, dict) and img.get("uri"):
                            return img["uri"].replace("\\/", "/")
                for v in d.values():
                    if isinstance(v, (dict, list)):
                        r = find_thumbnail(v, depth+1)
                        if r:
                            return r
            elif isinstance(d, list):
                for item in d:
                    if isinstance(item, (dict, list)):
                        r = find_thumbnail(item, depth+1)
                        if r:
                            return r
            return None
        meta["thumbnail"] = find_thumbnail(node)
        # Group/Page name for context
        to_field = node.get("to")
        if isinstance(to_field, dict) and to_field.get("name"):
            if meta["uploader"]:
                meta["uploader"] = f"{meta['uploader']}"
        return meta
    
    # Apply GraphQL metadata if og: tags were missing
    if target_nodes:
        for node in target_nodes:
            gql_meta = extract_graphql_metadata(node)
            if gql_meta["uploader"] and uploader == "Facebook User":
                uploader = gql_meta["uploader"]
            if gql_meta["title"] and (not title or title.startswith("Facebook Post by")):
                title = gql_meta["title"]
                # Truncate very long titles
                if len(title) > 200:
                    title = title[:197] + "..."
            if gql_meta["thumbnail"] and not thumbnail:
                thumbnail = gql_meta["thumbnail"]
            break
    
    # Update title if still generic
    if not title or title.startswith("Facebook Post by"):
        if uploader != "Facebook User":
            title = f"Facebook Post by {uploader}"
            
    # Scan album scripts globally to append all album photos
    if album_scripts:
        logger.info("Globally scanning album scripts for photos...")
        for script_text in album_scripts:
            try:
                data = json.loads(script_text)
                search_graphql(data)
            except:
                pass
 
    # Fallback to extracting image URLs directly from the HTML if none were found via JSON script blocks
    if not images:
        logger.info("No images found in JSON script blocks. Attempting direct HTML regex extraction...")
        raw_urls = re.findall(r'https://[^\s"\'\\<>]+(?:fbcdn\.net|scontent)[^\s"\'\\<>]+', html)
        for raw_url in raw_urls:
            clean_url = raw_url.replace("\\/", "/").replace("\\u0025", "%").replace("\\", "")
            clean_url = urllib.parse.unquote(clean_url)
            
            if is_valid_photo(clean_url):
                filename = extract_filename(clean_url)
                if filename and filename not in added_image_filenames:
                    added_image_filenames.add(filename)
                    images.append({
                        "label": f"Photo {len(images)+1}",
                        "url": clean_url,
                        "ext": "jpg"
                    })

    # If we found no photos but found og:image, add it
    if not images and thumbnail:
        images.append({
            "label": "Thumbnail",
            "url": thumbnail,
            "ext": "jpg"
        })
        
    # Always append actual photo options to video_options if we found photos via GraphQL
    # (i.e. not just the og:image fallback Thumbnail)
    for idx, img_obj in enumerate(images):
        if img_obj["label"] != "Thumbnail" or not video_options:
            video_options.append({
                "format_id": f"direct_photo_{idx+1}",
                "ext": "jpg",
                "resolution": "Original",
                "size": "Unknown Size",
                "label": f"Photo Option {idx+1}" if img_obj["label"] == "Thumbnail" else img_obj["label"],
                "url": img_obj["url"]
            })
 
    is_story = "/stories/" in url.lower()
    has_real_video = any(o.get("ext") == "mp4" or "video" in o.get("format_id", "") for o in video_options)
    
    if is_story:
        platform_label = "Facebook Story"
        platform_class = "facebook-story"
    elif has_real_video:
        platform_label = "Facebook Video"
        platform_class = "facebook"
    else:
        platform_label = "Facebook Post"
        platform_class = "facebook"
    likes = "N/A"
    if likes_val is not None:
        likes = str(likes_val)
    elif title:
        likes_match = re.search(r'\b([\d.,]+[KMB]?)\s*(?:lượt thích|likes|cảm xúc|người thích|reactions)', title, re.IGNORECASE)
        if likes_match:
            likes = likes_match.group(1).strip()

    return {
        "status": "success",
        "title": title,
        "duration": "0:30" if has_real_video else None,
        "uploader": uploader,
        "thumbnail": thumbnail or (images[0]["url"] if images else ""),
        "views": "N/A",
        "likes": likes,
        "upload_date": "Recent",
        "category": "Facebook Story" if is_story else "Facebook Post",
        "tags": ["Story"] if is_story else ["Post"],
        "subtitles": [],
        "video_options": video_options,
        "audio_options": [],
        "images": images,
        "platform": "Facebook",
        "platform_label": platform_label,
        "platform_class": platform_class
    }


def extract_facebook_story(url, client_id=None):
    client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt") if client_id else None
    if not client_cookies or not os.path.exists(client_cookies):
        raise ValueError("Cookies are required to download Facebook Stories. Please export and upload your cookies first.")
        
    try:
        import subprocess
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
        
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=15)
        html = result.stdout
        
        if "Sorry, something went wrong" in html or len(html) < 20000:
            if "login.php" in html or "login_form" in html:
                raise PermissionError("Unable to authenticate with Facebook. Your uploaded cookies may be expired or invalid. Please re-export and upload them.")
            raise PermissionError("Facebook returned an error or blocked the request. Please check if your cookies file is valid and active.")

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
            raise ValueError("Could not find any video or photo resources in the Story. The story may have expired or been deleted.")

        thumbnail = unique_photo_urls[0] if unique_photo_urls else "https://www.facebook.com/images/assets_files/yoodle/yoodle_default.png"
        
        images = []
        for idx, p_url in enumerate(unique_photo_urls):
            images.append({
                "label": f"Story Thumbnail {idx+1}",
                "url": p_url,
                "ext": "jpg"
            })

        resolve_facebook_sizes(video_options, client_id)

        return {
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
            "platform_label": "Facebook Story",
            "platform_class": "facebook-story"
        }
    except Exception as e:
        if isinstance(e, (ValueError, PermissionError)):
            raise e
        raise RuntimeError(f"Failed to extract Facebook Story contents: {e}")


def resolve_facebook_sizes(video_options, client_id=None):
    from concurrent.futures import ThreadPoolExecutor
    
    cookies_dir = os.path.join(TEMP_DOWNLOAD_DIR, "cookies")
    cookie_file = os.path.join(cookies_dir, f"cookies_{client_id}.txt") if client_id else None
    
    def resolve_fb_size(opt):
        url_to_check = opt.get("url")
        if url_to_check:
            s_bytes = get_url_content_length(url_to_check, cookies_file=cookie_file)
            if s_bytes:
                opt["size"] = format_size(s_bytes)
                
    if video_options:
        with ThreadPoolExecutor(max_workers=min(10, len(video_options))) as executor:
            list(executor.map(resolve_fb_size, video_options))

