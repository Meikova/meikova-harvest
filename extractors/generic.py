import re
import logging
import base64
import json
import requests
from urllib.parse import urlparse, urljoin, parse_qs
from concurrent.futures import ThreadPoolExecutor
import socket

from utils.helpers import get_url_content_length, format_size

logger = logging.getLogger(__name__)

# --- DNS Hijack Bypass Monkeypatch for curl_cffi ---
doh_cache = {}

def resolve_doh_helper(domain):
    # Skip DoH for localhost or IP addresses
    if not domain or domain.replace('.', '').isdigit() or domain in ['localhost', '127.0.0.1', '::1']:
        return []
    if domain in doh_cache:
        return doh_cache[domain]
        
    # Try Cloudflare DoH
    try:
        url = f"https://cloudflare-dns.com/dns-query?name={domain}&type=A"
        headers = {"Accept": "application/dns-json"}
        resp = requests.get(url, headers=headers, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            ips = []
            for answer in data.get("Answer", []):
                if answer.get("type") == 1: # A record
                    ips.append(answer.get("data"))
            if ips:
                doh_cache[domain] = ips
                return ips
    except Exception:
        pass
        
    # Try Google DoH as fallback
    try:
        url = f"https://dns.google/resolve?name={domain}&type=A"
        resp = requests.get(url, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            ips = []
            for answer in data.get("Answer", []):
                if answer.get("type") == 1: # A record
                    ips.append(answer.get("data"))
            if ips:
                doh_cache[domain] = ips
                return ips
    except Exception:
        pass
        
    return []

try:
    from curl_cffi import Curl, CurlOpt
    
    original_setopt = Curl.setopt
    
    def custom_setopt(self, opt, value):
        if opt == CurlOpt.URL:
            url_str = value.decode('utf-8') if isinstance(value, bytes) else str(value)
            try:
                parsed = urlparse(url_str)
                domain = parsed.netloc
                if ":" in domain:
                    domain = domain.split(":")[0]
                    
                if domain:
                    # Resolve via DoH first
                    real_ips = resolve_doh_helper(domain)
                    
                    # Check system DNS resolution
                    is_hijacked = False
                    try:
                        addr_info = socket.getaddrinfo(domain, 443)
                        system_ips = [info[4][0] for info in addr_info]
                        if "127.0.0.1" in system_ips or "::1" in system_ips:
                            is_hijacked = True
                        elif real_ips and not any(sip in real_ips for sip in system_ips):
                            is_hijacked = True
                    except Exception:
                        is_hijacked = True
                        
                    if is_hijacked and real_ips:
                        # Apply CURLOPT_RESOLVE
                        resolve_list = [f"{domain}:443:{real_ips[0]}".encode('utf-8')]
                        logger.info(f"[DNS Hijack Bypass] Overriding resolution for {domain} to {real_ips[0]}")
                        original_setopt(self, CurlOpt.RESOLVE, resolve_list)
            except Exception as e:
                logger.warning(f"DNS hijack intercept setopt failed: {e}")
                
        return original_setopt(self, opt, value)
        
    Curl.setopt = custom_setopt
    logger.info("curl_cffi DNS hijack monkeypatch installed successfully.")
except Exception as e:
    logger.warning(f"Failed to install curl_cffi DNS hijack monkeypatch: {e}")


def fetch_html(url, headers=None, cookies=None):
    if not headers:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    
    # Try using curl-cffi requests with manual redirect loop to allow monkeypatched DNS resolution on each hop
    try:
        from curl_cffi import requests as curl_requests
        current_url = url
        max_redirects = 5
        html_content = ""
        
        for redirect_hop in range(max_redirects):
            resp = curl_requests.get(
                current_url,
                headers=headers,
                cookies=cookies,
                impersonate="chrome",
                verify=False,
                allow_redirects=False,
                timeout=15
            )
            if resp.status_code in [301, 302, 307, 308]:
                location = resp.headers.get("Location")
                if location:
                    current_url = urljoin(current_url, location)
                    continue
            
            if resp.status_code == 200:
                html_content = resp.text
            else:
                html_content = resp.text
            break
            
        if html_content:
            return html_content
            
    except Exception as e:
        logger.warning(f"curl_cffi fetch_html failed: {e}. Trying standard requests fallback...")
        
    # Fallback to standard requests (with manual redirect loop & temporary monkeypatched DNS)
    original_getaddrinfo = socket.getaddrinfo
    try:
        current_url = url
        max_redirects = 5
        
        for redirect_hop in range(max_redirects):
            parsed = urlparse(current_url)
            domain = parsed.netloc
            if ":" in domain:
                domain = domain.split(":")[0]
                
            real_ips = resolve_doh_helper(domain)
            is_hijacked = False
            try:
                addr_info = original_getaddrinfo(domain, 443)
                system_ips = [info[4][0] for info in addr_info]
                if "127.0.0.1" in system_ips or "::1" in system_ips:
                    is_hijacked = True
                elif real_ips and not any(sip in real_ips for sip in system_ips):
                    is_hijacked = True
            except Exception:
                is_hijacked = True
                
            if is_hijacked and real_ips:
                def custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
                    if host == domain:
                        return original_getaddrinfo(real_ips[0], port, family, type, proto, flags)
                    return original_getaddrinfo(host, port, family, type, proto, flags)
                socket.getaddrinfo = custom_getaddrinfo
            else:
                socket.getaddrinfo = original_getaddrinfo
                
            resp = requests.get(current_url, headers=headers, cookies=cookies, verify=False, allow_redirects=False, timeout=15)
            if resp.status_code in [301, 302, 307, 308]:
                location = resp.headers.get("Location")
                if location:
                    current_url = urljoin(current_url, location)
                    continue
                    
            if resp.status_code == 200:
                return resp.text
            break
    except Exception as e:
        logger.error(f"Standard requests fallback fetch failed for {url}: {e}")
    finally:
        socket.getaddrinfo = original_getaddrinfo
        
    return ""

def resolve_hls_size(m3u8_url, referer=None):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if referer:
            headers["Referer"] = referer
            
        resp = requests.get(m3u8_url, headers=headers, verify=False, timeout=12)
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
            
        seg_resp = requests.head(target_segment, headers=headers, verify=False, timeout=12)
        content_len = seg_resp.headers.get("Content-Length")
        # If HEAD returned no Content-Length or a dummy/tiny content length (e.g. < 1000 bytes), fall back to GET
        if not content_len or int(content_len) < 1000:
            seg_resp = requests.get(target_segment, headers=headers, verify=False, stream=True, timeout=12)
            content_len = seg_resp.headers.get("Content-Length")
            
        if content_len:
            return int(content_len) * total_segments
    except Exception:
        pass
    return None


def generic_html_link_harvester(url, client_id):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    
    # Get page path segments
    path_segments = [seg for seg in parsed_url.path.split('/') if seg]
    last_segment = path_segments[-1] if path_segments else ""

    html = ""
    fetch_error_msg = ""
    
    # Load client cookies if available
    cookies_dict = {}
    if client_id:
        from config import TEMP_DOWNLOAD_DIR
        import os
        client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")
        if os.path.exists(client_cookies):
            try:
                with open(client_cookies, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.read().splitlines()
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("\t")
                    if len(parts) >= 7:
                        cookie_domain = parts[0].lower().lstrip('.')
                        if cookie_domain in url.lower():
                            cookies_dict[parts[5]] = parts[6]
            except Exception as e:
                logger.warning(f"Failed to read client cookies in generic harvester: {e}")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # Fetch raw HTML using our curl-cffi helper with cookies
        html = fetch_html(url, headers, cookies=cookies_dict)
        if not html:
            fetch_error_msg = "Failed to fetch HTML content (Connection error or Cloudflare protection)"
    except Exception as e:
        fetch_error_msg = str(e)

    if not html:
        # Construct fallback info even without HTML access
        title = last_segment or domain
        description = f"Unable to connect or analyze directly from the website ({fetch_error_msg}). This option allows you to download the raw webpage as an HTML file."
        
        video_options = [{
            "format_id": "generic_fallback",
            "resolution": "Webpage Content",
            "ext": "html",
            "type": "webpage",
            "size": "Unknown Size",
            "label": "Download Webpage (HTML / Text)",
            "url": url
        }]
        
        return {
            "status": "success",
            "title": title,
            "uploader": domain,
            "duration": "Unknown",
            "duration_raw": 0,
            "thumbnail": "",
            "is_shorts": False,
            "platform_label": domain.capitalize(),
            "platform_class": "default",
            "views": "—",
            "likes": "—",
            "upload_date": "—",
            "description": description,
            "category": "Web Page",
            "tags": [],
            "video_options": video_options,
            "audio_options": [],
            "subtitles": {},
            "images": [],
        }

    try:
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

        # Check if the page is a movie landing page (not a player page itself)
        # Landing pages don't have player option components but link to episode pages.
        has_player = ("dooplay_player_option" in clean_html or 
                      "streaming-server" in clean_html or 
                      "chooseStreamingServer" in clean_html or
                      "class=\"play-video\" data-link=" in clean_html or
                      "class='play-video' data-link=" in clean_html or
                      "player_option" in clean_html or
                      "embed_player" in clean_html)
                      
        if not has_player:
            # Try to find the first episode link or a watch movie link
            ep_link_match = re.search(r'href=["\']([^"\']+/tap-1_[^"\']+\.html)["\']', clean_html)
            if not ep_link_match:
                ep_link_match = re.search(r'href=["\']([^"\']+/tap-\d+_[^"\']+\.html)["\']', clean_html)
            if not ep_link_match:
                ep_link_match = re.search(r'href=["\']([^"\']+/tap-[^"\']+\.html)["\']', clean_html)
            if not ep_link_match:
                # Support WordPress DooPlay episodes and other clean URL structures
                ep_link_match = re.search(r'href=["\']([^"\']*(?:/episodes/|/tap-|/episode-|/ep-|[-_]tap-)[^"\']*(?:tap|tập|episode|ep)[-_\s]?0*1/?)["\']', clean_html, re.IGNORECASE)
            if not ep_link_match:
                ep_link_match = re.search(r'href=["\']([^"\']*(?:/episodes/|/tap-|/episode-|/ep-|[-_]tap-)[^"\']*)["\']', clean_html, re.IGNORECASE)
                
            if ep_link_match:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                first_ep_url = urljoin(url, ep_link_match.group(1))
                logger.info(f"Overview page detected. Fetching first episode URL: {first_ep_url}")
                html_ep = fetch_html(first_ep_url, headers, cookies=cookies_dict)
                if html_ep:
                    html = html_ep
                    clean_html = html.replace('\\/', '/').replace('\\', '')
                    url = first_ep_url
                    parsed_url = urlparse(url)
                    domain = parsed_url.netloc
                    path_segments = [seg for seg in parsed_url.path.split('/') if seg]
                    last_segment = path_segments[-1] if path_segments else ""
                    # Re-extract Title
                    title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
                    title = title_match.group(1).strip() if title_match else "Web Video"

        # Define nested helper function to extract options from a single HTML page
        def extract_single_page_options(page_html, page_url, page_domain, page_path_segments, page_last_segment):
            opts = []
            seen = set()
            
            # Determine title for current page
            t_match = re.search(r'<title>(.*?)</title>', page_html, re.IGNORECASE)
            page_title = t_match.group(1).strip() if t_match else "Web Video"
            
            # Extract main movie ID
            main_movie_id = ""
            movie_match = re.search(r'"movie"\s*:\s*\{\s*"id"\s*:\s*"(\d+)"', page_html)
            if movie_match:
                main_movie_id = movie_match.group(1)
            if not main_movie_id:
                movie_match = re.search(r'"movieId"\s*:\s*"([a-zA-Z0-9_-]+)"', page_html)
                if movie_match:
                    main_movie_id = movie_match.group(1)
            if not main_movie_id:
                movie_match = re.search(r'"postId"\s*:\s*(\d+)', page_html)
                if movie_match:
                    main_movie_id = movie_match.group(1)
                    
            # Determine episode name dynamically
            ep_name = "1"
            ep_match = re.search(r'(?:Tập|Tap|Episode|Ep)\s*(\d+)', page_title, re.IGNORECASE)
            if ep_match:
                ep_name = ep_match.group(1)
            else:
                last_seg = page_path_segments[-1] if page_path_segments else ""
                url_ep_match = re.search(r'(?:tap|episode|ep)[-_]?(\d+)', last_seg, re.IGNORECASE)
                if url_ep_match:
                    ep_name = url_ep_match.group(1)
                else:
                    digit_match = re.search(r'-(\d+)$', last_seg)
                    if digit_match:
                        ep_name = digit_match.group(1)
                        
            # 4. DooPlay players
            li_tags = re.findall(r'<li[^>]+class=["\'][^"\']*dooplay_player_option[^"\']*["\'][^>]*>.*?</li>', page_html, re.IGNORECASE | re.DOTALL)
            if li_tags:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                ajax_url = f"{urlparse(page_url).scheme}://{page_domain}/wp-admin/admin-ajax.php"
                for tag in li_tags:
                    try:
                        post_m = re.search(r'data-post=["\'](\d+)["\']', tag)
                        nume_m = re.search(r'data-nume=["\'](\d+)["\']', tag)
                        type_m = re.search(r'data-type=["\']([^"\']+)["\']', tag)
                        
                        if post_m and nume_m:
                            post_id = post_m.group(1)
                            nume = nume_m.group(1)
                            dtype = type_m.group(1) if type_m else "tv"
                            
                            title_m = re.search(r'<span class=["\']title["\']>(.*?)</span>', tag, re.IGNORECASE)
                            t_val = title_m.group(1).strip() if title_m else f"Option {nume}"
                            
                            ajax_headers = {
                                "User-Agent": headers["User-Agent"],
                                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                                "Referer": page_url
                            }
                            ajax_data = {
                                "action": "doo_player_ajax",
                                "post": post_id,
                                "nume": nume,
                                "type": dtype
                            }
                            
                            ajax_resp = requests.post(ajax_url, headers=ajax_headers, data=ajax_data, cookies=cookies_dict, verify=False, timeout=15)
                            if ajax_resp.status_code == 200:
                                res_json = ajax_resp.json()
                                embed_url = res_json.get("embed_url")
                                if embed_url:
                                    stream_url = embed_url
                                    resolved = False
                                    
                                    parsed_embed = urlparse(embed_url)
                                    queries = parse_qs(parsed_embed.query)
                                    for val_list in queries.values():
                                        for val in val_list:
                                            if val.startswith("http" ) and (".m3u8" in val or ".mp4" in val):
                                                stream_url = val
                                                resolved = True
                                                break
                                        if resolved:
                                            break
                                    
                                    if not resolved:
                                        embed_resp = requests.get(embed_url, headers={"User-Agent": headers["User-Agent"], "Referer": page_url}, cookies=cookies_dict, verify=False, timeout=15)
                                        if embed_resp.status_code == 200:
                                            embed_html = embed_resp.text
                                            obf_match = re.search(r'id=["\']player["\'][^>]+data-obf=["\']([^"\']+)["\']', embed_html) or \
                                                        re.search(r'data-obf=["\']([^"\']+)["\'][^>]+id=["\']player["\']', embed_html)
                                            if obf_match:
                                                try:
                                                    decoded_obf = json.loads(base64.b64decode(obf_match.group(1)).decode('utf-8'))
                                                    s_ub_val = decoded_obf.get("sUb")
                                                    if s_ub_val:
                                                        stream_url = urljoin(embed_url, f"/{s_ub_val}.m3u8")
                                                        resolved = True
                                                except Exception:
                                                    pass
                                                    
                                            if not resolved:
                                                url_match = re.search(r'const\s+url\s*=\s*["\']([^"\']+)["\']', embed_html)
                                                if url_match:
                                                    stream_url = urljoin(embed_url, url_match.group(1))
                                                    resolved = True
                                                else:
                                                    src_match = re.search(r'(?:file|source|url)\s*:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', embed_html, re.IGNORECASE)
                                                    if src_match:
                                                        stream_url = urljoin(embed_url, src_match.group(1))
                                                        resolved = True
                                                    else:
                                                        m3u8_matches = re.findall(r'https?://[^\s"\'\\<>#]+\.(?:m3u8|mp4)[^\s"\'\\<>#]*', embed_html)
                                                        if m3u8_matches:
                                                            stream_url = m3u8_matches[0]
                                                            resolved = True
                                    
                                    type_suffix = " [M3U8]" if (".m3u8" in stream_url) else " [EMBED]"
                                    label_name = f"Server: {t_val}{type_suffix}"
                                    if ep_name:
                                        label_name += f" (Episode {ep_name})"
                                        
                                    if stream_url not in seen:
                                        seen.add(stream_url)
                                        seen.add(embed_url)
                                        opts.append({
                                            "format_id": "",
                                            "resolution": "Auto Stream",
                                            "ext": "mp4",
                                            "type": "video",
                                            "size": "Unknown Size",
                                            "label": label_name,
                                            "episode": ep_name,
                                            "server": f"Server: {t_val}{type_suffix}",
                                            "url": stream_url
                                        })
                    except Exception as ex:
                        logger.warning(f"Failed to parse DooPlay option: {ex}")
                        
            # 5. Check data-link elements
            data_link_elements = re.findall(r'<a[^>]+data-link=["\']([^"\']+)["\'][^>]*>(.*?)</a>', page_html, re.IGNORECASE | re.DOTALL)
            if data_link_elements:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                for embed_url, inner_text in data_link_elements:
                    try:
                        t_val = re.sub(r'<[^>]+>', '', inner_text).strip()
                        t_val = t_val if t_val else "Server"
                        
                        stream_url = embed_url
                        resolved = False
                        
                        parsed_embed = urlparse(embed_url)
                        queries = parse_qs(parsed_embed.query)
                        for val_list in queries.values():
                            for val in val_list:
                                if val.startswith("http") and (".m3u8" in val or ".mp4" in val):
                                    stream_url = val
                                    resolved = True
                                    break
                            if resolved:
                                break
                        
                        is_direct = (stream_url.endswith('.m3u8') or '.m3u8' in stream_url or 
                                     stream_url.endswith('.mp4') or '.mp4' in stream_url)
                                     
                        if not resolved and not is_direct:
                            embed_resp = requests.get(embed_url, headers={"User-Agent": headers["User-Agent"], "Referer": page_url}, cookies=cookies_dict, verify=False, timeout=15)
                            if embed_resp.status_code == 200:
                                embed_html = embed_resp.text
                                obf_match = re.search(r'id=["\']player["\'][^>]+data-obf=["\']([^"\']+)["\']', embed_html) or \
                                            re.search(r'data-obf=["\']([^"\']+)["\'][^>]+id=["\']player["\']', embed_html)
                                if obf_match:
                                    try:
                                        decoded_obf = json.loads(base64.b64decode(obf_match.group(1)).decode('utf-8'))
                                        s_ub_val = decoded_obf.get("sUb")
                                        if s_ub_val:
                                            stream_url = urljoin(embed_url, f"/{s_ub_val}.m3u8")
                                            resolved = True
                                    except Exception:
                                        pass
                                        
                                if not resolved:
                                    url_match = re.search(r'const\s+url\s*=\s*["\']([^"\']+)["\']', embed_html)
                                    if url_match:
                                        stream_url = urljoin(embed_url, url_match.group(1))
                                        resolved = True
                                    else:
                                        src_match = re.search(r'(?:file|source|url)\s*:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', embed_html, re.IGNORECASE)
                                        if src_match:
                                            stream_url = urljoin(embed_url, src_match.group(1))
                                            resolved = True
                                        else:
                                            m3u8_matches = re.findall(r'https?://[^\s"\'\\<>#]+\.(?:m3u8|mp4)[^\s"\'\\<>#]*', embed_html)
                                            if m3u8_matches:
                                                stream_url = m3u8_matches[0]
                                                resolved = True
                        
                        type_suffix = " [M3U8]" if (".m3u8" in stream_url) else " [EMBED]"
                        label_name = f"Server: {t_val}{type_suffix}"
                        if ep_name:
                            label_name += f" (Episode {ep_name})"
                            
                        if stream_url not in seen:
                            seen.add(stream_url)
                            seen.add(embed_url)
                            opts.append({
                                "format_id": "",
                                "resolution": "Auto Stream",
                                "ext": "mp4",
                                "type": "video",
                                "size": "Unknown Size",
                                "label": label_name,
                                "episode": ep_name,
                                "server": f"Server: {t_val}{type_suffix}",
                                "url": stream_url
                            })
                    except Exception as ex:
                        logger.warning(f"Failed to parse data-link option: {ex}")
                        
            # 6. JSON database episode structures
            episode_pattern = r'\{[^{}]*"server"[^{}]*"name"[^{}]*"slug"[^{}]*"link"[^{}]*\}'
            ep_matches = re.findall(episode_pattern, page_html)
            
            for ep_str in ep_matches:
                try:
                    if not ep_str.startswith('{'): ep_str = '{' + ep_str
                    if not ep_str.endswith('}'): ep_str = ep_str + '}'
                    
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
                            if 'fcloud.live' in page_html:
                                media_url = 'https://fcloud.live' + media_url
                            else:
                                media_url = f"https://{page_domain}" + media_url
                                
                        slug_val = slug.group(1) if slug else ""
                        name_val = name.group(1) if name else ""
                        server_val = server.group(1) if server else "Server"
                        
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
                            if media_url not in seen:
                                seen.add(media_url)
                                opts.append(option_obj)
                except Exception:
                    pass
                    
            # 7. HTML5 fallback
            if not opts:
                video_tags = re.findall(r'<video[^>]*>.*?</video>', page_html, re.IGNORECASE | re.DOTALL)
                for vtag in video_tags:
                    srcs = re.findall(r'src=["\']([^"\']+)["\']', vtag, re.IGNORECASE)
                    for src in srcs:
                        src_url = urljoin(page_url, src)
                        if src_url not in seen:
                            seen.add(src_url)
                            opts.append({
                                "format_id": "",
                                "resolution": "HTML5 Video",
                                "ext": "mp4",
                                "type": "video",
                                "size": "Unknown Size",
                                "label": f"HTML5 Stream #{len(opts)+1} (Episode {ep_name})",
                                "episode": ep_name,
                                "server": "HTML5 Video",
                                "url": src_url
                            })
                source_tags = re.findall(r'<source[^>]+src=["\']([^"\']+)["\']', page_html, re.IGNORECASE)
                for src in source_tags:
                    src_url = urljoin(page_url, src)
                    if src_url not in seen:
                        seen.add(src_url)
                        opts.append({
                            "format_id": "",
                            "resolution": "HTML5 Source",
                            "ext": "mp4",
                            "type": "video",
                            "size": "Unknown Size",
                            "label": f"HTML5 Source #{len(opts)+1} (Episode {ep_name})",
                            "episode": ep_name,
                            "server": "HTML5 Source",
                            "url": src_url
                        })
                        
            # 8. Raw links
            if not opts:
                raw_m3u8_links = re.findall(r'https?://[^\s"\'\\<>#]+\.(?:m3u8|mp4)[^\s"\'\\<>#]*', page_html)
                for link in raw_m3u8_links:
                    link = link.rstrip('\\').rstrip('"').rstrip("'")
                    if link not in seen:
                        seen.add(link)
                        opts.append({
                            "format_id": "",
                            "resolution": "Auto Stream",
                            "ext": "mp4",
                            "type": "video",
                            "size": "Unknown Size",
                            "label": f"Direct Link #{len(opts)+1} (Episode {ep_name})",
                            "episode": ep_name,
                            "server": "Direct Link",
                            "url": link
                        })
                        
            # Filter duplicates for the same (server, episode) to keep only the best working stream
            best_opts = {}
            for opt in opts:
                server_key = opt["server"]
                ep_key = opt["episode"]
                key = (server_key, ep_key)
                
                if key not in best_opts:
                    best_opts[key] = opt
                else:
                    existing = best_opts[key]
                    existing_has_size = (existing.get("size") != "Unknown Size")
                    opt_has_size = (opt.get("size") != "Unknown Size")
                    
                    if opt_has_size and not existing_has_size:
                        best_opts[key] = opt
                    elif not opt_has_size and existing_has_size:
                        pass
                    else:
                        existing_is_streamc = ("streamc.xyz" in existing.get("url", ""))
                        opt_is_streamc = ("streamc.xyz" in opt.get("url", ""))
                        if existing_is_streamc and not opt_is_streamc:
                            best_opts[key] = opt
            
            return list(best_opts.values())

        # Find all other episode links on the page (overview page / playlist detection)
        def get_episode_num(ep_url):
            match = re.search(r'(?:tap|episode|ep)[-_\s]?(\d+)', ep_url, re.IGNORECASE)
            return int(match.group(1)) if match else 999999

        all_ep_urls = []
        seen_ep_urls = set()
        
        # Regex to find links that look like tap-1, tap-2, tap-10, episode-1, ep-1, etc.
        for match in re.findall(r'href=["\']([^"\']*(?:/episodes/|/tap-|/episode-|/ep-|[-_]tap-)[^"\']*)["\']', clean_html, re.IGNORECASE):
            full_ep_url = urljoin(url, match)
            if full_ep_url not in seen_ep_urls:
                ep_num = get_episode_num(full_ep_url)
                if ep_num != 999999:
                    seen_ep_urls.add(full_ep_url)
                    all_ep_urls.append(full_ep_url)
            
        all_ep_urls.sort(key=get_episode_num)

        video_options = []
        seen_urls = set()

        if len(all_ep_urls) > 1:
            logger.info(f"Overview or multi-episode page detected. Found {len(all_ep_urls)} episodes. Fetching in parallel...")
            
            # Limit to at most 48 episodes
            target_ep_urls = all_ep_urls[:48]
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            def fetch_and_extract(ep_url):
                try:
                    ep_html = fetch_html(ep_url, headers, cookies=cookies_dict)
                    if ep_html:
                        parsed_segments = [seg for seg in urlparse(ep_url).path.split('/') if seg]
                        parsed_last = parsed_segments[-1] if parsed_segments else ""
                        return extract_single_page_options(
                            ep_html.replace('\\/', '/').replace('\\', ''),
                            ep_url,
                            domain,
                            parsed_segments,
                            parsed_last
                        )
                except Exception as ex:
                    logger.warning(f"Failed to fetch/extract episode {ep_url}: {ex}")
                return []
                
            with ThreadPoolExecutor(max_workers=min(8, len(target_ep_urls))) as executor:
                results = list(executor.map(fetch_and_extract, target_ep_urls))
                
            for res_opts in results:
                for opt in res_opts:
                    if opt["url"] not in seen_urls:
                        seen_urls.add(opt["url"])
                        video_options.append(opt)
        else:
            # Single page or no other episodes found
            video_options = extract_single_page_options(
                clean_html,
                url,
                domain,
                path_segments,
                last_segment
            )

        # Assign format_ids dynamically to the final list
        for idx, opt in enumerate(video_options):
            opt["format_id"] = f"direct_video_{idx+1}"

        # 5. Ultimate Fallback: Add generic fallback webpage download if no options found
        if not video_options:
            video_options.append({
                "format_id": "generic_fallback",
                "resolution": "Webpage Content",
                "ext": "html",
                "type": "webpage",
                "size": "Unknown Size",
                "label": "Download Webpage (HTML / Text)",
                "url": url
            })
            
        # Resolve HLS / Direct CDN stream sizes in parallel
        if video_options:
            def resolve_opt_size(opt):
                opt_url = opt.get("url")
                if not opt_url:
                    return
                try:
                    # Resolve direct media URL inside embed player parameters if any
                    actual_url = opt_url
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
                        
                    if size_bytes and size_bytes >= 1024 * 1024:  # Ignore sizes < 1MB
                        opt["size"] = format_size(size_bytes)
                except Exception:
                    pass
                    
            with ThreadPoolExecutor(max_workers=min(15, len(video_options))) as executor:
                list(executor.map(resolve_opt_size, video_options))
                
            # Final deduplication on the combined video_options list (now that sizes are resolved!)
            best_opts = {}
            for opt in video_options:
                server_key = opt.get("server") or ""
                ep_key = opt.get("episode") or ""
                key = (server_key, ep_key)
                
                if key not in best_opts:
                    best_opts[key] = opt
                else:
                    existing = best_opts[key]
                    existing_has_size = (existing.get("size") != "Unknown Size")
                    opt_has_size = (opt.get("size") != "Unknown Size")
                    
                    if opt_has_size and not existing_has_size:
                        best_opts[key] = opt
                    elif not opt_has_size and existing_has_size:
                        pass
                    else:
                        existing_is_streamc = ("streamc.xyz" in existing.get("url", ""))
                        opt_is_streamc = ("streamc.xyz" in opt.get("url", ""))
                        if existing_is_streamc and not opt_is_streamc:
                            best_opts[key] = opt
                            
            video_options = list(best_opts.values())
            
            # Re-assign format_ids dynamically after filtering
            for idx, opt in enumerate(video_options):
                opt["format_id"] = f"direct_video_{idx+1}"
            
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
