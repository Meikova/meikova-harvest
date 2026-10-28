import os
import re
import logging
import base64
import json
import requests
from urllib.parse import urlparse, urljoin, parse_qs, unquote
from concurrent.futures import ThreadPoolExecutor
import socket

from utils.helpers import get_url_content_length, format_size, get_referer_by_url

logger = logging.getLogger(__name__)

# --- AD or tracking domains to skip during Iframe harvesting ---
AD_OR_TRACKING_DOMAINS = [
    "googlesyndication.com", "doubleclick.net", "googleads", "analytics.google.com",
    "facebook.com/plugins", "facebook.com/v2.", "platform.twitter.com",
    "disqus.com", "giscus.app", "histats.com", "addthis.com", "sharethis.com",
    "recaptcha", "google.com/recaptcha", "hcaptcha.com", "adsense", "analytics",
    "adnxs.com", "adsystem.com", "adservice.google.com", "google-analytics.com"
]

def check_drm(stream_url, referer=None):
    if not stream_url:
        return False
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if referer:
            headers["Referer"] = referer
            
        parsed = urlparse(stream_url)
        path = parsed.path.lower()
        query = parsed.query.lower()
        if not (path.endswith('.m3u8') or '.m3u8' in path or '.m3u8' in query or 
                path.endswith('.mpd') or '.mpd' in path or '.mpd' in query or 
                '/player/master/' in path):
            return False
            
        from curl_cffi import requests as curl_requests
        resp = curl_requests.get(stream_url, headers=headers, impersonate="chrome", verify=False, stream=True, timeout=3)
        if resp.status_code == 200:
            content = resp.content[:30000].decode('utf-8', errors='ignore')
            
            # HLS DRM indicators
            if "#EXT-X-KEY" in content:
                for line in content.splitlines():
                    if line.startswith("#EXT-X-KEY:"):
                        if "METHOD=SAMPLE-AES" in line or "METHOD=SAMPLE-AES-CTR" in line or "METHOD=SAMPLE-AES-CENC" in line:
                            return True
                        if any(k in line.lower() for k in ["widevine", "fairplay", "playready", "clearkey"]):
                            return True
            if "#EXT-X-SESSION-KEY" in content:
                return True
                
            # DASH DRM indicators
            if "<mpd" in content.lower() or "<period" in content.lower():
                if any(uuid in content.lower() for uuid in [
                    "edef8ba9-79d6-4ace-a3c8-27dcd51d21ed", # Widevine
                    "9a04f079-9840-4286-ab92-e65be0885f95", # PlayReady
                    "294b615b-edc3-4a1e-8c38-580718d711d4", # FairPlay
                    "1077efec-c0b2-4d02-ace3-3c1e52e2fb4b", # ClearKey
                ]):
                    return True
                if "contentprotection" in content.lower() and ("uuid" in content.lower() or "schemeiduri" in content.lower()):
                    return True
    except Exception as e:
        logger.warning(f"Error checking DRM for {stream_url}: {e}")
    return False

# --- DNS Hijack Bypass Monkeypatch for curl_cffi ---
doh_cache = {}

DOH_IP_MAP = {
    "cloudflare-dns.com": "1.1.1.1",
    "dns.google": "8.8.8.8",
    "dns.adguard.com": "94.140.14.14",
    "doh.opendns.com": "208.67.222.222",
    "animevietsub.sale": "172.67.72.243",
    "animevietsub.meme": "172.67.72.243"
}

def test_ip_connection(ip):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.4)  # 400ms timeout
        s.connect((ip, 443))
        s.close()
        return ip, True
    except Exception:
        return ip, False

def prioritize_ips(ips):
    if len(ips) <= 1:
        return ips
    working_ips = []
    blocked_ips = []
    # Fast parallel check for working IPs
    with ThreadPoolExecutor(max_workers=len(ips)) as executor:
        results = list(executor.map(test_ip_connection, ips))
        for ip, is_working in results:
            if is_working:
                working_ips.append(ip)
            else:
                blocked_ips.append(ip)
    return working_ips + blocked_ips

def resolve_doh_helper(domain):
    if not domain:
        return []
    if domain in DOH_IP_MAP:
        return [DOH_IP_MAP[domain]]
    if domain.replace('.', '').isdigit() or domain in ['localhost', '127.0.0.1', '::1']:
        return []
    if domain in doh_cache:
        return doh_cache[domain]
        
    from curl_cffi import requests as curl_requests
    ips = []
    
    # 1. Try Cloudflare DoH
    try:
        url = f"https://cloudflare-dns.com/dns-query?name={domain}&type=A"
        headers = {"Accept": "application/dns-json"}
        resp = curl_requests.get(url, headers=headers, impersonate="chrome", timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            for answer in data.get("Answer", []):
                if answer.get("type") == 1: # A record
                    ips.append(answer.get("data"))
    except Exception:
        pass
        
    # 2. Try Google DoH
    if not ips:
        try:
            url = f"https://dns.google/resolve?name={domain}&type=A"
            resp = curl_requests.get(url, impersonate="chrome", timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                for answer in data.get("Answer", []):
                    if answer.get("type") == 1: # A record
                        ips.append(answer.get("data"))
        except Exception:
            pass
        
    # 3. Try AdGuard DoH
    if not ips:
        try:
            url = f"https://dns.adguard.com/resolve?name={domain}&type=A"
            resp = curl_requests.get(url, impersonate="chrome", timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                for answer in data.get("Answer", []):
                    if answer.get("type") == 1: # A record
                        ips.append(answer.get("data"))
        except Exception:
            pass

    # 4. Try OpenDNS DoH
    if not ips:
        try:
            url = f"https://doh.opendns.com/dns-query?name={domain}&type=A"
            headers = {"Accept": "application/dns-json"}
            resp = curl_requests.get(url, headers=headers, impersonate="chrome", timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                for answer in data.get("Answer", []):
                    if answer.get("type") == 1: # A record
                        ips.append(answer.get("data"))
        except Exception:
            pass
        
    if ips:
        # Prioritize working IPs first to eliminate timeout issues on blocked IPs
        ips = prioritize_ips(ips)
        doh_cache[domain] = ips
        return ips
        
    return []

try:
    from curl_cffi import Curl, CurlOpt
    
    original_setopt = Curl.setopt
    
    def custom_setopt(self, opt, value):
        if opt == CurlOpt.URL:
            try:
                original_setopt(self, CurlOpt.IPRESOLVE, 1)
            except Exception:
                pass
            url_str = value.decode('utf-8') if isinstance(value, bytes) else str(value)
            try:
                parsed = urlparse(url_str)
                domain = parsed.netloc
                if ":" in domain:
                    domain = domain.split(":")[0]
                    
                if domain:
                    if "animevietsub" in domain.lower():
                        avs_ip = DOH_IP_MAP.get(domain.lower(), "172.67.72.243")
                        resolve_list = [
                            f"{domain}:80:{avs_ip}".encode('utf-8'),
                            f"{domain}:443:{avs_ip}".encode('utf-8')
                        ]
                        original_setopt(self, CurlOpt.RESOLVE, resolve_list)
                        return original_setopt(self, opt, value)
                    if domain in DOH_IP_MAP:
                        # Direct static IP override for DoH providers to prevent infinite recursion and bypass hijacking
                        resolve_list = [
                            f"{domain}:80:{DOH_IP_MAP[domain]}".encode('utf-8'),
                            f"{domain}:443:{DOH_IP_MAP[domain]}".encode('utf-8')
                        ]
                        original_setopt(self, CurlOpt.RESOLVE, resolve_list)
                        return original_setopt(self, opt, value)
                        
                    # Resolve via DoH first
                    real_ips = resolve_doh_helper(domain)
                    
                    if real_ips:
                        # Apply CURLOPT_RESOLVE for the single, working IP to bypass local DNS resolution entirely
                        working_ip = real_ips[0]
                        resolve_list = [
                            f"{domain}:80:{working_ip}".encode('utf-8'),
                            f"{domain}:443:{working_ip}".encode('utf-8')
                        ]
                        logger.info(f"[DNS Bypass] Overriding resolution for {domain} to {working_ip}")
                        original_setopt(self, CurlOpt.RESOLVE, resolve_list)
            except Exception as e:
                logger.warning(f"DNS hijack intercept setopt failed: {e}")
                
        return original_setopt(self, opt, value)
        
    Curl.setopt = custom_setopt
    logger.info("curl_cffi DNS hijack monkeypatch installed successfully.")
except Exception as e:
    logger.warning(f"Failed to install curl_cffi DNS hijack monkeypatch: {e}")

# --- Global DNS-over-HTTPS monkeypatch for python socket ---
original_getaddrinfo = socket.getaddrinfo

def custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host and "animevietsub" in host.lower():
        ip = DOH_IP_MAP.get(host.lower(), "172.67.72.243")
        return original_getaddrinfo(ip, port, socket.AF_INET, type, proto, flags)
    if host and host not in ['localhost', '127.0.0.1', '::1'] and not host.replace('.', '').isdigit():
        try:
            real_ips = resolve_doh_helper(host)
            if real_ips:
                results = []
                for ip in real_ips:
                    try:
                        res = original_getaddrinfo(ip, port, family, type, proto, flags)
                        results.extend(res)
                    except Exception:
                        pass
                if results:
                    return results
        except Exception:
            pass
    return original_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = custom_getaddrinfo
logger.info("Global socket.getaddrinfo DNS hijack monkeypatch installed successfully.")



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
        
    # Fallback to standard requests (with manual redirect loop)
    try:
        current_url = url
        max_redirects = 5
        
        for redirect_hop in range(max_redirects):
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
        
    return ""

def fetch_html_with_redirect(url, headers=None, cookies=None):
    if not headers:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    current_url = url
    try:
        from curl_cffi import requests as curl_requests
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
            return html_content, current_url
            
    except Exception as e:
        logger.warning(f"curl_cffi fetch_html_with_redirect failed: {e}. Trying standard requests fallback...")
        
    # Fallback to standard requests
    try:
        max_redirects = 5
        html_content = ""
        for redirect_hop in range(max_redirects):
            resp = requests.get(current_url, headers=headers, cookies=cookies, verify=False, allow_redirects=False, timeout=15)
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
            
        return html_content, current_url
    except Exception as e:
        logger.warning(f"Fallback requests fetch_html_with_redirect failed: {e}")
        return "", current_url

def resolve_hls_size(m3u8_url, referer=None):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if referer:
            headers["Referer"] = referer
            
        from curl_cffi import requests as curl_requests
        resp = curl_requests.get(m3u8_url, headers=headers, impersonate="chrome", verify=False, timeout=10)
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
            
        from curl_cffi import requests as curl_requests
        seg_resp = curl_requests.head(target_segment, headers=headers, impersonate="chrome", verify=False, timeout=10)
        content_len = seg_resp.headers.get("Content-Length")
        # If HEAD returned no Content-Length or a dummy/tiny content length (e.g. < 1000 bytes), fall back to GET
        if not content_len or int(content_len) < 1000:
            from curl_cffi import requests as curl_requests
            seg_resp = curl_requests.get(target_segment, headers=headers, impersonate="chrome", verify=False, stream=True, timeout=12)
            content_len = seg_resp.headers.get("Content-Length")
            
        if content_len:
            return int(content_len) * total_segments
    except Exception:
        pass
    return None


def unpack_dean_edwards(packed_str: str) -> str:
    """
    Unpacks Dean Edwards packed JavaScript:
    eval(function(p,a,c,k,e,d){...}('payload', base, count, 'k1|k2|...'.split('|'), ...))
    """
    # ponytail: regex-based Dean Edwards unpacker without external JS engine
    pattern = r"eval\(function\(p,a,c,k,e,[rd]\)\{.*?\}\s*\(\s*(['\"][^'\"]*['\"]|.*?)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(['\"][^'\"]*['\"])\.split\(['\"]([^'\"]+)['\"]\)"
    match = re.search(pattern, packed_str, re.DOTALL)
    if not match:
        return packed_str

    payload = match.group(1).strip()
    if (payload.startswith("'") and payload.endswith("'")) or (payload.startswith('"') and payload.endswith('"')):
        payload = payload[1:-1]
    
    radix = int(match.group(2))
    count = int(match.group(3))
    symtab = match.group(4).strip()[1:-1].split(match.group(5))

    def baseN(num, b):
        digits = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if num == 0:
            return digits[0]
        res = []
        while num > 0:
            res.append(digits[num % b])
            num //= b
        return "".join(reversed(res))

    lookup = {}
    for i in range(count):
        key = baseN(i, radix)
        val = symtab[i] if i < len(symtab) and symtab[i] else key
        lookup[key] = val

    def replace_word(m):
        w = m.group(0)
        return lookup.get(w, w)

    unpacked = re.sub(r"\b\w+\b", replace_word, payload)
    if "eval(function(p,a,c,k,e," in unpacked:
        return unpack_dean_edwards(unpacked)
    return unpacked


def deobfuscate_script(script_text: str) -> str:
    """
    Unpacks Dean Edwards, decodes hex/unicode escapes, and expands obfuscated strings.
    """
    if not script_text:
        return ""
    out = script_text
    # 1. Unpack Dean Edwards
    if "eval(function(p,a,c,k,e," in out:
        try:
            out = unpack_dean_edwards(out)
        except Exception:
            pass

    # 2. Decode hex escapes (\x68\x74\x74\x70...)
    if r"\x" in out:
        try:
            out = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), out)
        except Exception:
            pass

    # 3. Decode unicode escapes (\u002f...)
    if r"\u" in out:
        try:
            out = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), out)
        except Exception:
            pass

    # 4. Normalize escaped slashes
    out = out.replace(r"\/", "/")
    return out


def scan_text_for_media_urls(text: str, base_url: str = "") -> list:
    """
    Deep scan text/script for any media URLs (.m3u8, .mpd, .mp4, .mp3, audio & video streams)
    """
    if not text:
        return []
    candidates = []
    # 1. Direct URLs with extension (video and audio formats)
    pattern = r'(https?:\\?/\\?/[^\s"\'<>#]+?\.(?:m3u8|mpd|mp4|webm|mkv|ts|avi|mov|flv|m4v|mp3|m4a|wav|flac|aac|ogg|opus)(?:[^\s"\'<>#]*))'
    for m in re.findall(pattern, text, re.IGNORECASE):
        clean_url = m.replace(r"\/", "/").rstrip('\\').rstrip('"').rstrip("'")
        candidates.append(clean_url)

    # 2. Object keys: file, source, src, stream_url, audio_url
    kv_pattern = r'(?:file|source|src|stream|url|video_url|audio_url|stream_url)\s*[:=]\s*["\'](https?:\\?/\\?/[^"\']+)["\']'
    for m in re.findall(kv_pattern, text, re.IGNORECASE):
        clean_url = m.replace(r"\/", "/").rstrip('\\').rstrip('"').rstrip("'")
        candidates.append(clean_url)

    # 3. Base64 strings that decode to media URLs or JSON with media URLs
    b64_pattern = r'["\'](aHR0c[A-Za-z0-9+/=]{20,})["\']'
    for m in re.findall(b64_pattern, text):
        try:
            decoded = base64.b64decode(m).decode('utf-8', errors='ignore')
            if "http" in decoded and any(ext in decoded.lower() for ext in (".m3u8", ".mp4", ".mpd", ".mp3", ".m4a", ".webm")):
                sub_candidates = scan_text_for_media_urls(decoded, base_url)
                candidates.extend(sub_candidates)
        except Exception:
            pass

    # Deduplicate preserving order
    seen = set()
    result = []
    for c in candidates:
        if c not in seen and not any(bad in c.lower() for bad in ['beacon', 'analytics', 'pixel', 'advert', 'tracker']):
            seen.add(c)
            result.append(c)
    return result


DIRECT_MEDIA_EXTENSIONS = (
    ".m3u8", ".mpd", ".mp4", ".webm", ".mkv", ".avi", ".mov", ".flv", ".ts", ".m4v",
    ".mp3", ".m4a", ".wav", ".flac", ".aac", ".ogg", ".opus", ".wma"
)


def is_direct_media_url(url: str) -> bool:
    """Checks if a URL directly points to an audio or video stream/file."""
    if not url or not isinstance(url, str):
        return False
    if url.startswith("data:") or url.startswith("blob:"):
        return False
    try:
        parsed = urlparse(url)
        if not parsed.scheme or parsed.scheme.lower() not in ("http", "https"):
            return False
        path = parsed.path.lower()
        if any(path.endswith(ext) for ext in DIRECT_MEDIA_EXTENSIONS):
            return True
        # Check query string params (e.g., ?file=...m3u8 or ?url=...mp4)
        if any(f"{ext}?" in url.lower() or f"{ext}&" in url.lower() for ext in DIRECT_MEDIA_EXTENSIONS):
            return True
    except Exception:
        pass
    return False


def extract_direct_media_info(url, client_id=None):
    """
    Directly extracts metadata for raw media URLs (.m3u8, .mpd, .mp4, .webm, .mkv, .mp3, etc.)
    without invoking heavy external tools. Resolves HLS master variants into discrete quality tiers.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or "direct"
        path = unquote(parsed.path)

        filename = path.split("/")[-1] if "/" in path else "media"
        if not filename or filename == "/":
            filename = "media_stream"

        base_name, raw_ext = os.path.splitext(filename)
        ext = raw_ext.lstrip(".").lower()
        if not ext and "?" in url:
            for q_ext in DIRECT_MEDIA_EXTENSIONS:
                if f"{q_ext}?" in url.lower() or f"{q_ext}&" in url.lower():
                    ext = q_ext.lstrip(".")
                    break
        if not ext:
            ext = "mp4"

        clean_title = re.sub(r'[-_+]', ' ', base_name).strip() or "Direct Stream"

        AUDIO_EXTS = {"mp3", "m4a", "wav", "flac", "aac", "ogg", "opus", "wma"}
        is_audio = ext in AUDIO_EXTS

        video_options = []
        audio_options = []

        # If HLS Playlist (.m3u8): attempt variant expansion
        if ext == "m3u8":
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": f"{parsed.scheme}://{domain}/"
            }
            try:
                from curl_cffi import requests as curl_requests
                resp = curl_requests.get(url, headers=headers, impersonate="chrome", verify=False, timeout=8)
                if resp.status_code == 200 and "#EXTM3U" in resp.text:
                    content = resp.text
                    # Check for Master Playlist with Stream Variants
                    if "#EXT-X-STREAM-INF" in content:
                        variant_lines = content.splitlines()
                        var_idx = 1
                        for i, line in enumerate(variant_lines):
                            if line.startswith("#EXT-X-STREAM-INF:"):
                                res_match = re.search(r'RESOLUTION=(\d+)x(\d+)', line)
                                height = res_match.group(2) if res_match else None

                                sub_url = None
                                for next_line in variant_lines[i+1:]:
                                    next_line = next_line.strip()
                                    if next_line and not next_line.startswith("#"):
                                        sub_url = urljoin(url, next_line)
                                        break

                                if sub_url:
                                    res_label = f"{height}p" if height else "Auto Stream"
                                    tag_label = "FHD" if height and int(height) >= 1080 else ("HD" if height and int(height) >= 720 else "SD")
                                    size_str = "Stream (HLS / HD)"
                                    try:
                                        est_size = resolve_hls_size(sub_url, referer=url)
                                        if est_size and est_size > 1024 * 1024:
                                            size_str = format_size(est_size)
                                    except Exception:
                                        pass
                                    video_options.append({
                                        "format_id": f"direct_video_{var_idx}",
                                        "resolution": res_label,
                                        "ext": "mp4",
                                        "type": "video",
                                        "size": size_str,
                                        "label": f"HLS Stream {res_label} [{tag_label}]",
                                        "url": sub_url
                                    })
                                    var_idx += 1
            except Exception as hls_err:
                logger.warning(f"Error fetching/parsing M3U8 master variants: {hls_err}")

            if not video_options:
                size_str = "Stream (HLS / HD)"
                try:
                    est_size = resolve_hls_size(url, referer=url)
                    if est_size and est_size > 1024 * 1024:
                        size_str = format_size(est_size)
                except Exception:
                    pass
                video_options.append({
                    "format_id": "direct_video_1",
                    "resolution": "HLS Stream",
                    "ext": "mp4",
                    "type": "video",
                    "size": size_str,
                    "label": f"Direct HLS Stream ({clean_title})",
                    "url": url
                })

        elif ext == "mpd":
            video_options.append({
                "format_id": "direct_video_1",
                "resolution": "DASH Stream",
                "ext": "mp4",
                "type": "video",
                "size": "Stream (DASH)",
                "label": f"Direct DASH Stream ({clean_title})",
                "url": url
            })

        elif is_audio:
            size_val = get_url_content_length(url)
            size_str = format_size(size_val) if size_val else "Unknown Size"
            audio_options.append({
                "format_id": "direct_audio_1",
                "resolution": "Audio File",
                "ext": ext,
                "type": "audio",
                "size": size_str,
                "label": f"Direct Audio: {clean_title} (.{ext})",
                "url": url
            })

        else:
            size_val = get_url_content_length(url)
            size_str = format_size(size_val) if size_val else "Unknown Size"
            video_options.append({
                "format_id": "direct_video_1",
                "resolution": "Direct Video",
                "ext": ext,
                "type": "video",
                "size": size_str,
                "label": f"Direct Video: {clean_title} (.{ext})",
                "url": url
            })

        return {
            "status": "success",
            "title": clean_title,
            "uploader": domain,
            "duration": "Unknown",
            "duration_raw": 0,
            "thumbnail": "",
            "is_shorts": False,
            "platform_label": "Direct Media Stream",
            "platform_class": "direct",
            "views": "—",
            "likes": "—",
            "upload_date": "—",
            "description": f"Direct media stream parsed from {domain}",
            "category": "Audio" if is_audio else "Video",
            "tags": [],
            "video_options": video_options,
            "audio_options": audio_options,
            "subtitles": {},
            "images": []
        }
    except Exception as e:
        logger.warning(f"Failed to parse direct media info for {url}: {e}")
        return None


def generic_html_link_harvester(url, client_id, html=None):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    
    # Track visited iframe URLs to prevent infinite recursion loop
    visited_iframe_urls = set()
    
    # Get page path segments
    path_segments = [seg for seg in parsed_url.path.split('/') if seg]
    last_segment = path_segments[-1] if path_segments else ""

    html_from_client = html
    html = ""
    fetch_error_msg = ""
    final_url = None
    cookies_dict = {}
    
    if html_from_client:
        logger.info("Using pre-fetched HTML content from client.")
        html = html_from_client
        final_url = url
    else:
        # Load client cookies if available
        if client_id:
            from utils.cookies import get_cookie_file_path
            client_cookies = get_cookie_file_path(client_id)
            if client_cookies and os.path.exists(client_cookies):
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
            # Fetch raw HTML and resolve the final redirected URL
            if "animevietsub" in url.lower():
                try:
                    from curl_cffi import requests as curl_requests
                    s = curl_requests.Session(curl_options={CurlOpt.IPRESOLVE: 1})
                    if cookies_dict:
                        s.cookies.update(cookies_dict)
                    avs_headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                        "Referer": f"{parsed_url.scheme}://{domain}/",
                    }
                    # Fast 2-step handshake: request URL directly; if 403, retry with set cookies
                    avs_resp = s.get(url, headers=avs_headers, impersonate="chrome", verify=False, timeout=10)
                    if avs_resp.status_code == 403 or "PLAYER_DATA" not in avs_resp.text:
                        avs_resp = s.get(url, headers=avs_headers, impersonate="chrome", verify=False, timeout=10)
                    resp_text = avs_resp.text
                    is_cloudflare_challenge = "Đang Kiểm Tra" in resp_text or "_cf_chl_opt" in resp_text or "challenge-platform" in resp_text
                    
                    if is_cloudflare_challenge:
                        logger.warning(f"AnimeVietSub: Cloudflare challenge detected (cookies expired or missing). Status: {avs_resp.status_code}")
                        html = ""
                        fetch_error_msg = "Cloudflare security challenge detected. Browser cookies need to be synced via the companion extension."
                    elif avs_resp.status_code == 200 or "PLAYER_DATA" in resp_text:
                        html = resp_text
                        final_url = avs_resp.url or url
                        if hasattr(s, "cookies") and s.cookies:
                            cookies_dict.update(dict(s.cookies))
                    else:
                        logger.warning(f"AnimeVietSub initial session fetch returned HTTP {avs_resp.status_code} and missing indicators")
                        html, final_url = fetch_html_with_redirect(url, headers, cookies=cookies_dict)
                except Exception as e_avs:
                    logger.warning(f"AnimeVietSub initial session fetch failed: {e_avs}. Falling back...")
                    html, final_url = fetch_html_with_redirect(url, headers, cookies=cookies_dict)
            else:
                html, final_url = fetch_html_with_redirect(url, headers, cookies=cookies_dict)
            
            if final_url:
                url = final_url
                parsed_url = urlparse(url)
                domain = parsed_url.netloc
                path_segments = [seg for seg in parsed_url.path.split('/') if seg]
                last_segment = path_segments[-1] if path_segments else ""
                
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

        has_player = ("dooplay_player_option" in clean_html or 
                      "streaming-server" in clean_html or 
                      "chooseStreamingServer" in clean_html or
                      "class=\"play-video\" data-link=" in clean_html or
                      "class='play-video' data-link=" in clean_html or
                      "player_option" in clean_html or
                      "embed_player" in clean_html or
                      "embed-player" in clean_html or
                      "rophim" in domain.lower() or
                      ("/xem-phim" in url.lower() and ("guphim" in domain.lower() or "luphim" in domain.lower() or "rophim" in domain.lower())) or
                      any(ind in clean_html for ind in ["player-wrapper", "video-player", "jwplayer", "plyr", "videojs", "artplayer", "dplayer", "id=\"player\"", "class=\"player\"", "__NEXT_DATA__", "self.__next_f"]))
                      
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
        def extract_single_page_options(page_html, page_url, page_domain, page_path_segments, page_last_segment, depth=0):
            opts = []
            seen = set()
            
            # Custom LuPhim.com Extractor
            if "luphim" in page_domain.lower():
                try:
                    import html as html_lib
                    from curl_cffi import requests as curl_requests
                    
                    iframe_match = re.search(r'<iframe[^>]+id="iframeStream"[^>]+src="([^"]+)"', page_html)
                    if not iframe_match:
                        iframe_match = re.search(r'<iframe[^>]+src="([^"]+moviking[^"]+)"', page_html)
                    if iframe_match:
                        raw_src = iframe_match.group(1)
                        unescaped_src = html_lib.unescape(raw_src)
                        iframe_url = urljoin(page_url, unescaped_src)
                        logger.info(f"[LuPhim Extractor] Found unescaped iframe URL: {iframe_url}")
                        
                        iframe_headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Referer": page_url
                        }
                        iframe_html = fetch_html(iframe_url, headers=iframe_headers, cookies=cookies_dict)
                        if iframe_html:
                            # 1. New Moviking layout: embeds cdn.codexa.fun/streaming3rd or similar player iframe
                            inner_iframe_m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', iframe_html)
                            if inner_iframe_m:
                                inner_src = html_lib.unescape(inner_iframe_m.group(1))
                                inner_url = urljoin(iframe_url, inner_src)
                                logger.info(f"[LuPhim Extractor] Found nested player iframe URL: {inner_url}")
                                
                                player_headers = {
                                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                                    "Referer": iframe_url
                                }
                                player_html = fetch_html(inner_url, headers=player_headers, cookies=cookies_dict)
                                if player_html:
                                    # Extract var url = 'https://...m3u8'
                                    stream_m = re.search(r"var\s+url\s*=\s*['\"]([^'\"]+\.m3u8[^'\"]*)['\"]", player_html)
                                    if not stream_m:
                                        stream_m = re.search(r"file:\s*['\"]([^'\"]+\.m3u8[^'\"]*)['\"]", player_html)
                                    if not stream_m:
                                        m3u8_links = re.findall(r'https?://[^\s"\'\\<>#]+\.m3u8[^\s"\'\\<>#]*', player_html)
                                        if m3u8_links:
                                            stream_m = re.search(r'(.*)', m3u8_links[0])
                                            
                                    if stream_m:
                                        direct_stream_url = stream_m.group(1)
                                        opts.append({
                                            "format_id": "",
                                            "resolution": "Auto Stream",
                                            "ext": "mp4",
                                            "type": "video",
                                            "size": "Unknown Size",
                                            "label": "Server: LuPhim [M3U8 Direct]",
                                            "episode": "Full",
                                            "server": "Server: LuPhim",
                                            "url": direct_stream_url,
                                            "referer": iframe_url
                                        })
                                        return opts

                            # 2. Legacy Moviking API layout (fallback)
                            videoId_m = re.search(r"var videoId\s*=\s*['\"]([^'\"]*)['\"]", iframe_html)
                            videoId = videoId_m.group(1) if videoId_m else None
                            cdn_m = re.search(r"var cdn\s*=\s*['\"]([^'\"]*)['\"]", iframe_html)
                            cdn = cdn_m.group(1) if cdn_m else "https://cdn3.codexa.fun"
                            web_m = re.search(r"var web\s*=\s*['\"]([^'\"]*)['\"]", iframe_html)
                            web = web_m.group(1) if web_m else "luphim.com"
                            lang_m = re.search(r"var lang\s*=\s*['\"]([^'\"]*)['\"]", iframe_html)
                            lang = lang_m.group(1) if lang_m else "vi"
                            domain_m = re.search(r"var domain\s*=\s*['\"]([^'\"]*)['\"]", iframe_html)
                            domain = domain_m.group(1) if domain_m else "https://luphim.com/"
                            
                            if videoId:
                                import random
                                visitor_id = "".join(random.choices("0123456789abcdef", k=32))
                                api_url = "https://moviking.neuronix.sbs/geturl"
                                api_headers = {
                                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                                    "Referer": iframe_url,
                                    "Origin": "https://moviking.neuronix.sbs",
                                    "X-Requested-With": "XMLHttpRequest"
                                }
                                api_data = {
                                    "renderer": "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0)",
                                    "id": visitor_id,
                                    "videoId": videoId,
                                    "domain": domain
                                }
                                api_resp = curl_requests.post(
                                    api_url,
                                    headers=api_headers,
                                    data=api_data,
                                    cookies=cookies_dict,
                                    impersonate="chrome",
                                    verify=False,
                                    timeout=15
                                )
                                if api_resp.status_code == 200:
                                    api_response = api_resp.text
                                    player_url = f"{cdn}/streaming?id={videoId}&subId=&web={web}&{api_response}&cdn={cdn}&lang={lang}"
                                    player_headers = {
                                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                                        "Referer": "https://moviking.neuronix.sbs/"
                                    }
                                    player_html = fetch_html(player_url, headers=player_headers, cookies=cookies_dict)
                                    if player_html:
                                        stream_match = re.search(r"var url\s*=\s*['\"]([^'\"]*)['\"]\s*\+\s*videoId\s*\+\s*['\"]([^'\"]*)['\"]", player_html)
                                        if stream_match:
                                            stream_url = f"{stream_match.group(1)}{videoId}{stream_match.group(2)}"
                                            if "?" in stream_url:
                                                stream_url += "&ext=.m3u8"
                                            else:
                                                stream_url += "?ext=.m3u8"
                                            opts.append({
                                                "format_id": "",
                                                "resolution": "Auto Stream",
                                                "ext": "mp4",
                                                "type": "video",
                                                "size": "Unknown Size",
                                                "label": "Server: Moviking [M3U8]",
                                                "episode": "Full",
                                                "server": "Server: Moviking",
                                                "url": stream_url,
                                                "referer": "https://moviking.neuronix.sbs/"
                                            })
                                            return opts
                except Exception as ex:
                    logger.warning(f"LuPhim Extractor failed: {ex}")

            # Custom RoPhim.soy Extractor
            if "rophim" in page_domain.lower():
                try:
                    from curl_cffi import requests as curl_requests
                    slug_match = re.search(r'/xem-phim/([^.?]+)', page_url)
                    if slug_match:
                        full_slug = slug_match.group(1)
                        movie_id = full_slug.split('.')[-1] if '.' in full_slug else full_slug
                        
                        api_headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Referer": page_url,
                            "Origin": f"https://{page_domain}"
                        }
                        
                        parsed_purl = urlparse(page_url)
                        p_qs = parse_qs(parsed_purl.query)
                        ver_param = p_qs.get("ver", ["1"])[0]
                        
                        getlink_url = f"https://api.rophim.stream/api/v1/player/getLink?movie_id={movie_id}"
                        getlink_resp = curl_requests.get(getlink_url, headers=api_headers, impersonate="chrome", verify=False, timeout=10)
                        
                        embed_base = ""
                        if getlink_resp.status_code == 200:
                            gl_data = getlink_resp.json()
                            if gl_data.get("status") and gl_data.get("result"):
                                embed_base = gl_data["result"]
                                
                        if not embed_base:
                            embed_base = f"https://api.rophim.stream/player/embed?id={movie_id}"
                            
                        # Fetch seasons for episodes
                        seasons_url = f"https://api.rophim.stream/api/v1/movie/seasons?mId={movie_id}"
                        seasons_resp = curl_requests.get(seasons_url, headers=api_headers, impersonate="chrome", verify=False, timeout=10)
                        
                        if seasons_resp.status_code == 200:
                            s_data = seasons_resp.json()
                            if s_data.get("status") and s_data.get("result"):
                                for season in s_data["result"]:
                                    s_num = season.get("season_number", 1)
                                    s_name = season.get("name", f"Season {s_num}")
                                    for ep in season.get("episodes", []):
                                        ep_num = ep.get("episode_number", 1)
                                        ep_name = (ep.get("name") or "").strip() or f"Tập {ep_num:02d}"
                                        ep_url = f"{embed_base}&version={ver_param}&season={s_num}&episode={ep_num}"
                                        
                                        opts.append({
                                            "format_id": "",
                                            "resolution": "Stream Player",
                                            "ext": "mp4",
                                            "type": "video",
                                            "size": "Unknown Size",
                                            "label": f"Server: RoPhim [Player] ({s_name} - {ep_name})",
                                            "episode": f"{ep_num}",
                                            "server": f"Server: RoPhim ({s_name})",
                                            "url": ep_url,
                                            "referer": page_url
                                        })
                                        
                        if not opts:
                            opts.append({
                                "format_id": "",
                                "resolution": "Stream Player",
                                "ext": "mp4",
                                "type": "video",
                                "size": "Unknown Size",
                                "label": "Server: RoPhim [Player] (Full Movie)",
                                "episode": "Full",
                                "server": "Server: RoPhim",
                                "url": f"{embed_base}&version={ver_param}",
                                "referer": page_url
                            })
                            
                        if opts:
                            return opts
                except Exception as ex:
                    logger.warning(f"RoPhim Extractor failed: {ex}")

            # Custom GuPhim.com Extractor
            if "guphim" in page_domain.lower():
                try:
                    # 1. Parse cdnHost from page_html
                    cdn_host_m = re.search(r'cdnHost\s*=\s*["\']([^"\']*)["\']', page_html)
                    cdn_host = cdn_host_m.group(1) if cdn_host_m else ""
                    if not cdn_host or cdn_host.startswith("/"):
                        cdn_host = "https://guphim.com"
                    
                    # 2. Extract slug from page_url
                    parsed_path = urlparse(page_url).path
                    slug_match = re.search(r'(.*?)-(\w{5})-tap-', parsed_path)
                    if slug_match:
                        slug_path = slug_match.group(0)[:-5]
                    else:
                        slug_path = parsed_path
                    
                    slug = slug_path.split("/xem-phim-")[-1]
                    
                    # 3. Find active episode hash from page_url or the HTML
                    ep_slug_m = re.search(r'[a-z0-9]{5}-tap-([a-zA-Z0-9-]+)', parsed_path)
                    target_ep_slug = ep_slug_m.group(1) if ep_slug_m else None
                    
                    a_tags = re.findall(r'<a\s+[^>]*class="[^"]*retrieve-ep[^"]*"[^>]*>', page_html)
                    if not a_tags:
                        a_tags = re.findall(r'<a\s+[^>]*data-ep="[^"]+"[^>]*>', page_html)
                        
                    ep_list = []
                    for tag in a_tags:
                        ep_m = re.search(r'data-ep="([^"]+)"', tag)
                        slug_m = re.search(r'data-ep_slug="([^"]+)"', tag)
                        if ep_m and slug_m:
                            ep_list.append((ep_m.group(1), slug_m.group(1)))
                    
                    active_ep_hash = None
                    if target_ep_slug and ep_list:
                        for ep_hash, ep_slug_val in ep_list:
                            if ep_slug_val == target_ep_slug:
                                active_ep_hash = ep_hash
                                break
                    if not active_ep_hash and ep_list:
                        active_ep_hash = ep_list[0][0]
                    if not active_ep_hash:
                        ep_general_m = re.search(r'data-ep="([^"]+)"', page_html)
                        if ep_general_m:
                            active_ep_hash = ep_general_m.group(1)
                    
                    if active_ep_hash:
                        api_url = f"{cdn_host}/api/v1/link/{slug}?e={active_ep_hash}"
                        logger.info(f"[GuPhim Extractor] Calling API: {api_url}")
                        
                        api_headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Referer": page_url,
                            "Accept": "application/json, text/javascript, */*; q=0.01",
                            "X-Requested-With": "XMLHttpRequest"
                        }
                        
                        from curl_cffi import requests as curl_requests
                        api_resp = curl_requests.get(
                            api_url,
                            headers=api_headers,
                            cookies=cookies_dict,
                            impersonate="chrome",
                            verify=False,
                            timeout=15
                        )
                        if api_resp.status_code == 200:
                            res_json = api_resp.json()
                            link_m3u8 = res_json.get("link_m3u8")
                            link_embed = res_json.get("link_embed")
                            title_val = res_json.get("title", target_ep_slug or "Full")
                            
                            stream_url = link_m3u8 or link_embed
                            type_suffix = " [M3U8]" if link_m3u8 else " [EMBED]"
                            
                            if stream_url:
                                label_name = f"Server: GuPhim{type_suffix} (Episode {title_val})"
                                opts.append({
                                    "format_id": "",
                                    "resolution": "Auto Stream",
                                    "ext": "mp4",
                                    "type": "video",
                                    "size": "Unknown Size",
                                    "label": label_name,
                                    "episode": title_val,
                                    "server": f"Server: GuPhim{type_suffix}",
                                    "url": stream_url
                                })
                                return opts
                except Exception as ex:
                    logger.warning(f"GuPhim Extractor failed: {ex}")

            # Custom AnimeVietSub Extractor
            if "animevietsub" in page_domain.lower():
                try:
                    import json as _json
                    from curl_cffi import requests as curl_requests

                    logger.info(f"[AnimeVietSub Extractor] Detected domain: {page_domain}")

                    # AnimeVietSub requires a curl_cffi session to bypass Cloudflare.
                    # The page_html passed in may have been fetched without session cookies
                    # (resulting in a 403 redirect page). We re-fetch with a proper session.
                    avs_session = curl_requests.Session(curl_options={CurlOpt.IPRESOLVE: 1})
                    if cookies_dict:
                        avs_session.cookies.update(cookies_dict)
                    avs_headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                        "Referer": f"https://{page_domain}/",
                    }

                    base_url = f"https://{page_domain}"
                    if page_html and "PLAYER_DATA" in page_html:
                        avs_html = page_html
                    else:
                        avs_resp = avs_session.get(page_url, impersonate="chrome", verify=False, timeout=10, headers=avs_headers)
                        if avs_resp.status_code == 403 or "PLAYER_DATA" not in avs_resp.text:
                            avs_resp = avs_session.get(page_url, impersonate="chrome", verify=False, timeout=10, headers=avs_headers)
                        if avs_resp.status_code not in (200, 520, 403) and "PLAYER_DATA" not in avs_resp.text:
                            logger.warning(f"[AnimeVietSub Extractor] Page fetch failed: HTTP {avs_resp.status_code}")
                            raise Exception(f"HTTP {avs_resp.status_code}")
                        avs_html = avs_resp.text

                    # Check if Next.js layout (animevietsub.my)
                    is_nextjs = "_next/static" in avs_html or "animevietsub.my" in page_domain.lower()
                    if is_nextjs:
                        logger.info(f"[AnimeVietSub Extractor] Parsing Next.js site: {page_url}")
                        
                        # Step 1: Parse Title
                        avs_title_m = re.search(r'<title>(.*?)</title>', avs_html, re.IGNORECASE)
                        avs_title = avs_title_m.group(1).strip() if avs_title_m else "AnimeVietSub Video"
                        avs_title = re.sub(r'^Xem\s+', '', avs_title, flags=re.IGNORECASE)
                        avs_title = re.sub(r'\s+Vietsub\s*-\s*AnimeVietsub$', '', avs_title, flags=re.IGNORECASE)
                        
                        # Step 2: Parse all episode links
                        raw_links = re.findall(r'href=["\'](/xem-phim/[^"\']+/tap-\d+/vietsub[^"\']*)["\']', avs_html)
                        
                        seen_eps = set()
                        clean_links = []
                        for ep in raw_links:
                            base_path = ep.split('?')[0]
                            ep_num_match = re.search(r'tap-(\d+)', base_path)
                            if ep_num_match:
                                ep_num = ep_num_match.group(1)
                                if ep_num not in seen_eps:
                                    seen_eps.add(ep_num)
                                    clean_links.append((ep_num, base_path))
                                    
                        clean_links.sort(key=lambda x: int(x[0]))
                        
                        if not clean_links:
                            play_match = re.search(r'href=["\'](/xem-phim/[^"\']+)["\']', avs_html)
                            if play_match:
                                play_url = urljoin(page_url, play_match.group(1))
                                play_resp = avs_session.get(play_url, impersonate="chrome", verify=False, timeout=15, headers=avs_headers)
                                if play_resp.status_code == 200:
                                    avs_html = play_resp.text
                                    raw_links = re.findall(r'href=["\'](/xem-phim/[^"\']+/tap-\d+/vietsub[^"\']*)["\']', avs_html)
                                    for ep in raw_links:
                                        base_path = ep.split('?')[0]
                                        ep_num_match = re.search(r'tap-(\d+)', base_path)
                                        if ep_num_match:
                                            ep_num = ep_num_match.group(1)
                                            if ep_num not in seen_eps:
                                                seen_eps.add(ep_num)
                                                clean_links.append((ep_num, base_path))
                                    clean_links.sort(key=lambda x: int(x[0]))
                                    
                        opts = []
                        if clean_links:
                            logger.info(f"[AnimeVietSub Extractor] Found {len(clean_links)} Next.js episodes")
                            for ep_num, base_path in clean_links:
                                ep_url = urljoin(page_url, base_path)
                                if base_path in page_url:
                                    ep_html = avs_html
                                else:
                                    try:
                                        ep_resp = avs_session.get(ep_url, impersonate="chrome", verify=False, timeout=10, headers=avs_headers)
                                        ep_html = ep_resp.text if ep_resp.status_code == 200 else ""
                                    except Exception:
                                        ep_html = ""
                                    
                                if ep_html:
                                    m3u8_links = re.findall(r'https?://[^\s"\'\\<>#]+\.m3u8[^\s"\'\\<>#]*', ep_html)
                                    if m3u8_links:
                                        stream_url = m3u8_links[0]
                                        opts.append({
                                            "format_id": "",
                                            "resolution": "Auto Stream",
                                            "ext": "mp4",
                                            "type": "video",
                                            "size": "Unknown Size",
                                            "label": f"Server: VIP Stream (Tập {ep_num})",
                                            "episode": ep_num,
                                            "server": "VIP Stream [M3U8]",
                                            "url": stream_url
                                        })
                            return opts

                    # Step 3: Parse anime title and metadata
                    avs_title_m = re.search(r'<h1[^>]*class="Title"[^>]*>(.*?)</h1>', avs_html, re.IGNORECASE | re.DOTALL)
                    avs_title = avs_title_m.group(1).strip() if avs_title_m else ""
                    if not avs_title:
                        avs_title_m = re.search(r'<title>(.*?)</title>', avs_html, re.IGNORECASE)
                        avs_title = avs_title_m.group(1).strip() if avs_title_m else "AnimeVietSub Video"

                    # Step 4: Parse the episode list from HTML
                    # Each episode: <a data-id="112740" title="Tập 01" href="...tap-01-112740.html" data-hash="...">01</a>
                    ep_pattern = re.compile(
                        r'<a\s+[^>]*data-id="(\d+)"[^>]*title="([^"]*)"[^>]*'
                        r'class="[^"]*btn-episode[^"]*"[^>]*href="([^"]*)"[^>]*'
                        r'data-hash="([^"]*)"[^>]*>([^<]*)</a>',
                        re.IGNORECASE | re.DOTALL
                    )
                    episodes = ep_pattern.findall(avs_html)

                    if not episodes:
                        # Try a more relaxed pattern
                        ep_pattern2 = re.compile(
                            r'<a\s+[^>]*data-id="(\d+)"[^>]*title="([^"]*)"[^>]*'
                            r'href="([^"]*)"[^>]*data-hash="([^"]*)"[^>]*>([^<]*)</a>',
                            re.IGNORECASE | re.DOTALL
                        )
                        episodes = ep_pattern2.findall(avs_html)

                    logger.info(f"[AnimeVietSub Extractor] Found {len(episodes)} episodes for '{avs_title}'")

                    # Step 5: Parse PLAYER_DATA from the current page (inline JS)
                    pd_match = re.search(r'window\.PLAYER_DATA\s*=\s*(\{.*?\});', avs_html)
                    current_pd = None
                    if pd_match:
                        try:
                            current_pd = _json.loads(pd_match.group(1))
                        except Exception:
                            pass

                    current_ep_id = None
                    if current_pd:
                        current_ep_id = str(current_pd.get("episode_id", ""))

                    url_ep_match = re.search(r'tap-(\d+)', page_url.lower())
                    url_ep_num = url_ep_match.group(1) if url_ep_match else ""

                    # Step 6: Build video options for each episode
                    for ep_data_id, ep_title_attr, ep_href, ep_hash, ep_text in episodes:
                        ep_num = ep_text.strip() or ep_title_attr.replace("Tập ", "").strip()
                        ep_label = ep_title_attr.strip() or f"Tập {ep_num}"

                        is_current = False
                        if current_ep_id and str(ep_data_id) == str(current_ep_id):
                            is_current = True
                        elif ep_href and (ep_href in page_url or page_url.endswith(ep_href)):
                            is_current = True
                        elif url_ep_num and (ep_num.lstrip('0') == url_ep_num.lstrip('0')):
                            is_current = True

                        iframe_link = None

                        # Check if this episode matches the current page's PLAYER_DATA
                        if current_pd and str(ep_data_id) == current_ep_id:
                            link_val = current_pd.get("link", "")
                            if isinstance(link_val, str) and link_val.startswith("http"):
                                iframe_link = link_val
                        
                        # If not the current episode, attempt to fetch its stream link
                        if not iframe_link and ep_href and len(opts) < 12:
                            try:
                                ep_full_url = ep_href if ep_href.startswith("http") else base_url + ep_href
                                ep_resp = avs_session.get(ep_full_url, impersonate="chrome", verify=False, timeout=3, headers=avs_headers)
                                if ep_resp.status_code == 403 or "PLAYER_DATA" not in ep_resp.text:
                                    ep_resp = avs_session.get(ep_full_url, impersonate="chrome", verify=False, timeout=3, headers=avs_headers)
                                if ep_resp.status_code in (200, 520, 403) or "PLAYER_DATA" in ep_resp.text:
                                    ep_pd_match = re.search(r'window\.PLAYER_DATA\s*=\s*(\{.*?\});', ep_resp.text)
                                    if ep_pd_match:
                                        try:
                                            ep_pd = _json.loads(ep_pd_match.group(1))
                                            link_val = ep_pd.get("link", "")
                                            if isinstance(link_val, str) and link_val.startswith("http"):
                                                iframe_link = link_val
                                        except Exception:
                                            pass
                            except Exception as ep_ex:
                                logger.debug(f"[AnimeVietSub Extractor] Individual fetch skipped for ep {ep_num}: {ep_ex}")

                        if iframe_link:
                            from urllib.parse import urlparse as _urlparse, parse_qs as _parse_qs, urlencode as _urlencode, urlunparse as _urlunparse
                            parsed_iframe = _urlparse(iframe_link)
                            if parsed_iframe.query:
                                iframe_qs = _parse_qs(parsed_iframe.query, keep_blank_values=True)
                                iframe_qs.pop("nextName", None)
                                iframe_qs.pop("nextUrl", None)
                                new_query = _urlencode(iframe_qs, doseq=True)
                                clean_iframe = _urlunparse(parsed_iframe._replace(query=new_query))
                            else:
                                clean_iframe = iframe_link
                        elif ep_href:
                            # Fallback: link to episode page directly so user can play/preview
                            clean_iframe = ep_href if ep_href.startswith("http") else base_url + ep_href
                        else:
                            clean_iframe = None

                        if clean_iframe:
                            opts.append({
                                "format_id": f"avs_ep_{ep_data_id}",
                                "resolution": "Web Stream (MSE)",
                                "ext": "mp4",
                                "type": "video",
                                "size": "Stream (MSE / HD)",
                                "label": f"Server: AnimeVsub [STREAM] ({ep_label})",
                                "episode": ep_num,
                                "server": "Server: AnimeVsub",
                                "url": clean_iframe,
                                "referer": f"https://{page_domain}/",
                                "is_current": is_current,
                            })
                            logger.info(f"[AnimeVietSub Extractor] Added {ep_label} (is_current={is_current}): {clean_iframe[:80]}...")

                    if opts:
                        return opts

                except Exception as ex:
                    import traceback
                    logger.warning(f"AnimeVietSub Extractor failed: {ex}\n{traceback.format_exc()}")
            
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
                            
                            from curl_cffi import requests as curl_requests
                            ajax_resp = curl_requests.post(
                                ajax_url,
                                headers=ajax_headers,
                                data=ajax_data,
                                cookies=cookies_dict,
                                impersonate="chrome",
                                verify=False,
                                timeout=15
                            )
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
                                        from curl_cffi import requests as curl_requests
                                        embed_resp = curl_requests.get(
                                            embed_url,
                                            headers={"User-Agent": headers["User-Agent"], "Referer": page_url},
                                            cookies=cookies_dict,
                                            impersonate="chrome",
                                            verify=False,
                                            timeout=15
                                        )
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
                                                deobf_embed = deobfuscate_script(embed_html)
                                                scanned_streams = scan_text_for_media_urls(deobf_embed, embed_url)
                                                if scanned_streams:
                                                    stream_url = scanned_streams[0]
                                                    resolved = True

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
                            from curl_cffi import requests as curl_requests
                            embed_resp = curl_requests.get(
                                embed_url,
                                headers={"User-Agent": headers["User-Agent"], "Referer": page_url},
                                cookies=cookies_dict,
                                impersonate="chrome",
                                verify=False,
                                timeout=15
                            )
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
                                    deobf_embed = deobfuscate_script(embed_html)
                                    scanned_streams = scan_text_for_media_urls(deobf_embed, embed_url)
                                    if scanned_streams:
                                        stream_url = scanned_streams[0]
                                        resolved = True

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
                    
            # 7. Schema.org JSON-LD VideoObject and AudioObject
            json_ld_blocks = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', page_html, re.IGNORECASE | re.DOTALL)
            for j_block in json_ld_blocks:
                try:
                    j_data = json.loads(j_block.strip())
                    items = []
                    if isinstance(j_data, list):
                        items = j_data
                    elif isinstance(j_data, dict):
                        if "@graph" in j_data and isinstance(j_data["@graph"], list):
                            items = j_data["@graph"]
                        else:
                            items = [j_data]
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        it_type = str(it.get("@type", "")).lower()
                        if any(k in it_type for k in ["video", "audio", "media"]):
                            content_url = it.get("contentUrl") or it.get("embedUrl")
                            if content_url and content_url.startswith("http") and content_url not in seen:
                                seen.add(content_url)
                                is_aud = "audio" in it_type or any(content_url.lower().endswith("." + a_ext) for a_ext in ["mp3", "m4a", "wav", "flac", "ogg", "aac", "opus", "wma"])
                                name_val = it.get("name") or it.get("headline") or "Schema Media"
                                opts.append({
                                    "format_id": "",
                                    "resolution": "Audio" if is_aud else "HD Stream",
                                    "ext": "mp3" if is_aud else "mp4",
                                    "type": "audio" if is_aud else "video",
                                    "size": "Unknown Size",
                                    "label": f"Schema.org: {name_val[:40]}",
                                    "episode": ep_name,
                                    "server": "Schema.org Audio" if is_aud else "Schema.org",
                                    "url": content_url
                                })
                except Exception:
                    pass

            # 8. OpenGraph & Twitter Media Tags
            og_video_matches = re.findall(r'<meta[^>]+(?:property|name)=["\'](?:og:video|og:video:url|og:video:secure_url|twitter:player:stream)["\'][^>]+content=["\']([^"\']+)["\']', page_html, re.IGNORECASE)
            for og_url in og_video_matches:
                og_url = urljoin(page_url, og_url)
                if og_url.startswith("http") and og_url not in seen:
                    seen.add(og_url)
                    opts.append({
                        "format_id": "",
                        "resolution": "Social Video",
                        "ext": "mp4",
                        "type": "video",
                        "size": "Unknown Size",
                        "label": f"OpenGraph Video #{len(opts)+1}",
                        "episode": ep_name,
                        "server": "OpenGraph",
                        "url": og_url
                    })

            og_audio_matches = re.findall(r'<meta[^>]+(?:property|name)=["\'](?:og:audio|og:audio:url|og:audio:secure_url)["\'][^>]+content=["\']([^"\']+)["\']', page_html, re.IGNORECASE)
            for og_a_url in og_audio_matches:
                og_a_url = urljoin(page_url, og_a_url)
                if og_a_url.startswith("http") and og_a_url not in seen:
                    seen.add(og_a_url)
                    opts.append({
                        "format_id": "",
                        "resolution": "Audio Stream",
                        "ext": "mp3",
                        "type": "audio",
                        "size": "Unknown Size",
                        "label": f"OpenGraph Audio #{len(opts)+1}",
                        "episode": ep_name,
                        "server": "OpenGraph Audio",
                        "url": og_a_url
                    })

            # 9. Modern Framework Payloads (__NEXT_DATA__, __NUXT__, window.__INITIAL_STATE__)
            next_data_match = re.search(r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', page_html, re.IGNORECASE | re.DOTALL)
            if next_data_match:
                found_in_next = scan_text_for_media_urls(next_data_match.group(1), page_url)
                for n_url in found_in_next:
                    if n_url not in seen:
                        seen.add(n_url)
                        is_aud = any(n_url.lower().endswith("." + a_ext) for a_ext in ["mp3", "m4a", "wav", "flac", "ogg", "aac", "opus", "wma"])
                        opts.append({
                            "format_id": "",
                            "resolution": "Next.js Audio" if is_aud else "Next.js Stream",
                            "ext": "mp3" if is_aud else "mp4",
                            "type": "audio" if is_aud else "video",
                            "size": "Unknown Size",
                            "label": f"Next.js Media #{len(opts)+1}",
                            "episode": ep_name,
                            "server": "Next.js Framework",
                            "url": n_url
                        })

            # 10. Universal Embedded Player Objects (JWPlayer, Video.js, Plyr, DPlayer, ArtPlayer)
            player_configs = re.findall(r'(?:jwplayer|videojs|Plyr|DPlayer|Artplayer)[^;{]*\{([^}]+)\}', page_html, re.IGNORECASE)
            for p_cfg in player_configs:
                cfg_streams = scan_text_for_media_urls(p_cfg, page_url)
                for p_url in cfg_streams:
                    if p_url not in seen:
                        seen.add(p_url)
                        opts.append({
                            "format_id": "",
                            "resolution": "Player Stream",
                            "ext": "mp4",
                            "type": "video",
                            "size": "Unknown Size",
                            "label": f"Embedded Player #{len(opts)+1}",
                            "episode": ep_name,
                            "server": "Web Player",
                            "url": p_url
                        })

            # 11. HTML5 Media tags (Video and Audio)
            video_tags = re.findall(r'<video[^>]*>.*?</video>', page_html, re.IGNORECASE | re.DOTALL)
            for vtag in video_tags:
                srcs = re.findall(r'src=["\']([^"\']+)["\']', vtag, re.IGNORECASE)
                for src in srcs:
                    src_url = urljoin(page_url, src)
                    if src_url not in seen and src_url.startswith("http"):
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

            audio_tags = re.findall(r'<audio[^>]*>.*?</audio>', page_html, re.IGNORECASE | re.DOTALL)
            for atag in audio_tags:
                srcs = re.findall(r'src=["\']([^"\']+)["\']', atag, re.IGNORECASE)
                for src in srcs:
                    src_url = urljoin(page_url, src)
                    if src_url not in seen and src_url.startswith("http"):
                        seen.add(src_url)
                        a_ext = src_url.rsplit(".", 1)[-1].split("?")[0].lower() if "." in src_url else "mp3"
                        if a_ext not in ["mp3", "m4a", "wav", "flac", "ogg", "aac", "opus", "wma"]:
                            a_ext = "mp3"
                        opts.append({
                            "format_id": "",
                            "resolution": "HTML5 Audio",
                            "ext": a_ext,
                            "type": "audio",
                            "size": "Unknown Size",
                            "label": f"HTML5 Audio #{len(opts)+1}",
                            "episode": ep_name,
                            "server": "HTML5 Audio",
                            "url": src_url
                        })

            # 12. Recursive iframe harvesting
            if depth < 3:
                import html as html_lib
                iframe_srcs = re.findall(r'<iframe[^>]+(?:src|data-src|data-lazy-src)=["\']([^"\']+)["\']', page_html, re.IGNORECASE)
                for src in iframe_srcs:
                    try:
                        src = html_lib.unescape(src)
                        iframe_url = urljoin(page_url, src)
                        if not iframe_url.startswith("http"):
                            continue
                        if iframe_url in visited_iframe_urls:
                            continue
                        visited_iframe_urls.add(iframe_url)
                        
                        parsed_iframe = urlparse(iframe_url)
                        iframe_domain = parsed_iframe.netloc.lower()
                        if not iframe_domain or any(ad in iframe_url.lower() for ad in AD_OR_TRACKING_DOMAINS):
                            continue

                        # Check query parameters for media stream URLs
                        if parsed_iframe.query:
                            iq_params = parse_qs(parsed_iframe.query)
                            for q_param in ("url", "source", "file", "v", "src", "link"):
                                for q_val in iq_params.get(q_param, []):
                                    if q_val.startswith("http") and any(ext_kw in q_val.lower() for ext_kw in (".m3u8", ".mpd", ".mp4")):
                                        if q_val not in seen:
                                            seen.add(q_val)
                                            opts.append({
                                                "format_id": "",
                                                "resolution": "Auto Stream",
                                                "ext": "mp4",
                                                "type": "video",
                                                "size": "Unknown Size",
                                                "label": f"Iframe Stream #{len(opts)+1} (Episode {ep_name})",
                                                "episode": ep_name,
                                                "server": f"Embed ({iframe_domain})",
                                                "url": q_val
                                            })
                            
                        logger.info(f"[Iframe Harvester] Fetching nested iframe at depth {depth+1}: {iframe_url}")
                        iframe_headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Referer": page_url
                        }
                        iframe_html = fetch_html(iframe_url, iframe_headers, cookies=cookies_dict)
                        if iframe_html:
                            # Scan all script tags in iframe_html using deobfuscator
                            iframe_scripts = re.findall(r'<script[^>]*>(.*?)</script>', iframe_html, re.IGNORECASE | re.DOTALL)
                            for iscript in iframe_scripts:
                                if iscript.strip():
                                    deobf_is = deobfuscate_script(iscript)
                                    for is_url in scan_text_for_media_urls(deobf_is, iframe_url):
                                        if is_url not in seen:
                                            seen.add(is_url)
                                            opts.append({
                                                "format_id": "",
                                                "resolution": "Auto Stream",
                                                "ext": "mp4",
                                                "type": "video",
                                                "size": "Unknown Size",
                                                "label": f"Iframe Stream #{len(opts)+1} (Episode {ep_name})",
                                                "episode": ep_name,
                                                "server": f"Embed ({iframe_domain})",
                                                "url": is_url
                                            })

                            clean_iframe_html = iframe_html.replace('\\/', '/').replace('\\', '')
                            iframe_path_segs = [seg for seg in parsed_iframe.path.split('/') if seg]
                            iframe_last = iframe_path_segs[-1] if iframe_path_segs else ""
                            
                            iframe_opts = extract_single_page_options(
                                clean_iframe_html,
                                iframe_url,
                                iframe_domain,
                                iframe_path_segs,
                                iframe_last,
                                depth = depth + 1
                            )
                            for opt in iframe_opts:
                                if not opt.get("server") or opt["server"] == "Direct Link":
                                    opt["server"] = f"Embed ({iframe_domain})"
                                opt["ext"] = "mp4"
                                opt["type"] = "video"
                                if opt["url"] not in seen:
                                    seen.add(opt["url"])
                                    opts.append(opt)
                    except Exception as ex:
                        logger.warning(f"Failed to fetch/extract iframe {src}: {ex}")

            # 13. Raw links & script-embedded stream definitions (Fallback when needed)
            if not opts:
                script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', page_html, re.IGNORECASE | re.DOTALL)
                scanned_links = []
                for s_block in script_blocks:
                    if s_block.strip():
                        deobf = deobfuscate_script(s_block)
                        found = scan_text_for_media_urls(deobf, page_url)
                        scanned_links.extend(found)
                
                deobf_page = deobfuscate_script(page_html)
                scanned_links.extend(scan_text_for_media_urls(deobf_page, page_url))
                
                raw_media_links = re.findall(r'https?://[^\s"\'\\<>#]+\.(?:m3u8|mpd|mp4|webm|mkv|mp3|m4a|wav|flac|ogg|aac|opus)[^\s"\'\\<>#]*', page_html, re.IGNORECASE)
                js_stream_links = re.findall(r'(?:file|source|url|src|stream)\s*[:=]\s*["\'](https?://[^\s"\'\\<>#]+\.(?:m3u8|mpd|mp4|webm|mkv|mp3|m4a|wav|flac|ogg|aac|opus)[^\s"\'\\<>#]*)["\']', page_html, re.IGNORECASE)
                all_raw_candidates = list(dict.fromkeys(scanned_links + raw_media_links + js_stream_links))
                for link in all_raw_candidates:
                    link = link.rstrip('\\').rstrip('"').rstrip("'")
                    if link not in seen:
                        seen.add(link)
                        ext_cand = link.split("?")[0].rsplit(".", 1)[-1].lower() if "." in link else "mp4"
                        AUDIO_EXTS_LIST = ["mp3", "m4a", "wav", "flac", "ogg", "aac", "opus", "wma"]
                        is_aud = ext_cand in AUDIO_EXTS_LIST or any(kw in link.lower() for kw in ["/audio/", "/podcast/", "type=audio"])
                        opts.append({
                            "format_id": "",
                            "resolution": "Direct Audio" if is_aud else "Auto Stream",
                            "ext": ext_cand if is_aud else "mp4",
                            "type": "audio" if is_aud else "video",
                            "size": "Unknown Size",
                            "label": f"Direct {'Audio' if is_aud else 'Link'} #{len(opts)+1} (Episode {ep_name})",
                            "episode": ep_name,
                            "server": "Direct Audio" if is_aud else "Direct Link",
                            "url": link
                        })

            # Filter duplicates for the same (server, episode) to keep only the best working stream
            best_opts = {}
            for opt in opts:
                server_key = opt.get("server") or ""
                ep_key = opt.get("episode") or ""
                is_generic_server = not server_key.startswith("Server:") or any(
                    gen_kw in server_key for gen_kw in ["Direct", "HTML5", "Schema", "OpenGraph", "Next.js", "Web Player", "Embed"]
                )
                if is_generic_server:
                    key = (opt.get("type", "video"), server_key, ep_key, opt.get("url", ""))
                else:
                    key = (opt.get("type", "video"), server_key, ep_key)
                
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
            if not full_ep_url.startswith("http"):
                continue
            if full_ep_url not in seen_ep_urls:
                ep_num = get_episode_num(full_ep_url)
                if ep_num != 999999:
                    seen_ep_urls.add(full_ep_url)
                    all_ep_urls.append(full_ep_url)
            
        all_ep_urls.sort(key=get_episode_num)

        video_options = []
        seen_urls = set()

        if len(all_ep_urls) > 1 and "animevietsub" not in domain.lower():
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

                    is_hls = (actual_url.endswith('.m3u8') or '.m3u8' in actual_url or '/player/master/' in actual_url)
                    is_dash = (actual_url.endswith('.mpd') or '.mpd' in actual_url)
                    
                    if is_hls:
                        referer_to_use = opt.get("referer") or get_referer_by_url(actual_url) or url
                        size_bytes = resolve_hls_size(actual_url, referer_to_use)
                    elif is_dash:
                        size_bytes = None
                    else:
                        size_bytes = get_url_content_length(actual_url)
                        
                    if size_bytes and size_bytes >= 1024 * 1024:  # Ignore sizes < 1MB
                        opt["size"] = format_size(size_bytes)
                    elif not opt.get("size") or opt.get("size") == "Unknown Size":
                        is_stream_opt = (
                            is_hls or is_dash or
                            "player" in str(opt.get("url", "")).lower() or
                            "stream" in str(opt.get("resolution", "")).lower() or
                            "stream" in str(opt.get("server", "")).lower() or
                            str(opt.get("format_id", "")).startswith("avs_")
                        )
                        if is_stream_opt:
                            dur = opt.get("duration")
                            if dur and isinstance(dur, (int, float)) and dur > 0:
                                est_bytes = int(dur * 275000)
                                opt["size"] = f"~{format_size(est_bytes)} (HD Stream)"
                            else:
                                opt["size"] = "Stream (MSE / HD)"
                        
                    if is_hls or is_dash:
                        referer_to_use = opt.get("referer") or get_referer_by_url(actual_url) or url
                        if check_drm(actual_url, referer_to_use):
                            opt["is_drm"] = True
                except Exception:
                    pass
                    
            with ThreadPoolExecutor(max_workers=min(30, len(video_options))) as executor:
                list(executor.map(resolve_opt_size, video_options))
                
            # Final deduplication on the combined video_options list (now that sizes are resolved!)
            best_opts = {}
            for opt in video_options:
                server_key = opt.get("server") or ""
                ep_key = opt.get("episode") or ""
                is_generic_server = not server_key.startswith("Server:") or any(
                    gen_kw in server_key for gen_kw in ["Direct", "HTML5", "Schema", "OpenGraph", "Next.js", "Web Player", "Embed"]
                )
                if is_generic_server:
                    key = (opt.get("type", "video"), server_key, ep_key, opt.get("url", ""))
                else:
                    key = (opt.get("type", "video"), server_key, ep_key)
                
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
                            
            final_video_opts = []
            final_audio_opts = []
            for opt in best_opts.values():
                if opt.get("type") == "audio":
                    final_audio_opts.append(opt)
                else:
                    final_video_opts.append(opt)

            current_format_id = None
            # Re-assign format_ids dynamically after filtering
            for idx, opt in enumerate(final_video_opts):
                opt["format_id"] = f"direct_video_{idx+1}"
                if opt.get("is_current") and not current_format_id:
                    current_format_id = opt["format_id"]

            for idx, opt in enumerate(final_audio_opts):
                opt["format_id"] = f"direct_audio_{idx+1}"

            category = "Web Video"
            if not final_video_opts and final_audio_opts:
                category = "Web Audio"
            
        return {
            "status": "success",
            "title": title,
            "uploader": domain,
            "duration": "Unknown",
            "duration_raw": 0,
            "thumbnail": thumbnail,
            "is_shorts": False,
            "platform_label": domain.capitalize() + (" Audio" if category == "Web Audio" else ""),
            "platform_class": "default",
            "views": "—",
            "likes": "—",
            "upload_date": "—",
            "description": description,
            "category": category,
            "tags": [],
            "video_options": final_video_opts,
            "current_format_id": current_format_id or (final_video_opts[0]["format_id"] if final_video_opts else (final_audio_opts[0]["format_id"] if final_audio_opts else None)),
            "audio_options": final_audio_opts,
            "subtitles": {},
            "images": [{"label": "Thumbnail", "url": thumbnail, "ext": "jpg"}] if thumbnail else [],
        }
    except Exception as err:
        logger.warning(f"generic_html_link_harvester failed: {err}")
        return None
