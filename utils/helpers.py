import os
import logging
import requests

logger = logging.getLogger(__name__)

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


def format_number(val):
    """Formats large numbers into K or M notation."""
    if val is None:
        return "N/A"
    try:
        val = int(val)
        if val >= 1_000_000:
            return f"{val / 1_000_000:.1f}M"
        elif val >= 1_000:
            return f"{val / 1_000:.1f}K"
        return str(val)
    except Exception:
        return str(val)


def get_referer_by_url(url):
    """Helper to return the correct Referer header based on the target URL domain."""
    if not url:
        return None
    url_lower = url.lower()
    if "tiktok" in url_lower or "tiktokcdn" in url_lower:
        return "https://www.tiktok.com/"
    elif "twitter" in url_lower or "x.com" in url_lower or "twimg" in url_lower:
        return "https://x.com/"
    elif "instagram" in url_lower or "cdninstagram" in url_lower:
        return "https://www.instagram.com/"
    elif "fbcdn" in url_lower or "facebook" in url_lower or "fbsbx" in url_lower:
        return "https://www.facebook.com/"
    elif "threads" in url_lower:
        return "https://www.threads.net/"
    elif "reddit" in url_lower or "redd.it" in url_lower:
        return "https://www.reddit.com/"
    elif "soundcloud" in url_lower or "sndcdn" in url_lower:
        return "https://soundcloud.com/"
    elif "pinterest" in url_lower or "pinimg" in url_lower:
        return "https://www.pinterest.com/"
    elif "vimeo" in url_lower or "vimeocdn" in url_lower:
        return "https://vimeo.com/"
    elif "youtube" in url_lower or "googlevideo" in url_lower:
        return "https://www.youtube.com/"
    elif "codexa.fun" in url_lower:
        return "https://moviking.neuronix.sbs/"
    elif "googleapiscdn.com" in url_lower:
        return "https://animevietsub.love/"
        
        
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}/"
    except Exception:
        pass
        
    return None


def get_url_content_length(url, cookies_file=None):
    """Fetches the Content-Length of a URL via HTTP HEAD request with redirects."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }
    
    req_headers = headers.copy()
    req_headers["Referer"] = get_referer_by_url(url)

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
            response = session.head(url, headers=req_headers, timeout=8, allow_redirects=True)
            if response.status_code not in [200, 206]:
                response = session.get(url, headers=req_headers, stream=True, timeout=8, allow_redirects=True)
        else:
            response = requests.head(url, headers=req_headers, timeout=8, allow_redirects=True)
            if response.status_code not in [200, 206]:
                response = requests.get(url, headers=req_headers, stream=True, timeout=8, allow_redirects=True)
            
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


def get_gallery_dl_path():
    """Resolve the path to the gallery-dl binary based on operating system."""
    import platform
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    is_windows = platform.system().lower().startswith("win")
    if is_windows:
        venv_path = os.path.join(base_dir, "venv", "Scripts", "gallery-dl.exe")
    else:
        venv_path = os.path.join(base_dir, "venv", "bin", "gallery-dl")
        
    if os.path.exists(venv_path):
        return venv_path
        
    return "gallery-dl" # Fallback to global PATH

