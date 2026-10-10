import json
import logging

logger = logging.getLogger(__name__)

def get_cookie_file_path(client_id=None):
    """Returns the cookie file path for the client, with multi-level fallback:
    1. Client-specific file (cookies_{client_id}.txt)
    2. Chrome extension file (cookies_chrome-extension.txt)
    3. Most recently modified cookie file in the cookies directory
    """
    from config import COOKIES_DIR, TEMP_DOWNLOAD_DIR
    import os
    
    cookies_dir = COOKIES_DIR
    if not os.path.isdir(cookies_dir):
        # Fallback to legacy location if not migrated yet
        legacy_dir = os.path.join(TEMP_DOWNLOAD_DIR, "cookies")
        if os.path.isdir(legacy_dir):
            cookies_dir = legacy_dir
        else:
            return None
    
    # Level 1: exact client match if provided
    if client_id:
        path = os.path.join(cookies_dir, f"cookies_{client_id}.txt")
        if os.path.exists(path):
            return path
    
    # Level 2: chrome-extension fallback
    ext_path = os.path.join(cookies_dir, "cookies_chrome-extension.txt")
    if os.path.exists(ext_path):
        return ext_path
    
    # Level 3: most recently modified cookie file (handles client ID mismatches)
    cookie_files = [
        os.path.join(cookies_dir, f) for f in os.listdir(cookies_dir)
        if f.startswith("cookies_") and f.endswith(".txt")
    ]
    if cookie_files:
        return max(cookie_files, key=os.path.getmtime)
    
    return os.path.join(cookies_dir, f"cookies_{client_id}.txt") if client_id else None

def parse_cookies_to_dict(content):
    """Parses raw cookie content (either JSON or Netscape format) into a structured dictionary."""
    import time
    cookies = {}
    stripped = content.strip()
    default_exp = str(int(time.time()) + 86400 * 365)  # 1 year in future
    now_ts = int(time.time())
    
    # Check if it's JSON
    if stripped.startswith("[") or stripped.startswith("{"):
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
                    
                    exp_val = cookie.get("expirationDate") or cookie.get("expires") or cookie.get("expiration")
                    try:
                        exp_num = int(float(exp_val)) if exp_val is not None else 0
                    except (ValueError, TypeError):
                        exp_num = 0
                        
                    # Session cookies (expiration=0) or past timestamps get auto-renewed to 1 year in future
                    # so that Python http.cookiejar (used by gallery-dl, yt-dlp, requests) won't discard them as expired.
                    if exp_num <= now_ts:
                        expiration = default_exp
                    else:
                        expiration = str(exp_num)
                        
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
            
            try:
                exp_num = int(float(expiration)) if expiration else 0
            except (ValueError, TypeError):
                exp_num = 0
                
            if exp_num <= now_ts:
                expiration = default_exp
                
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
    """Serializes a dictionary of cookies back into standard Netscape/curl cookiefile format."""
    import time
    default_exp = str(int(time.time()) + 86400 * 365)
    now_ts = int(time.time())
    
    lines = [
        "# Netscape HTTP Cookie File",
        "# http://curl.haxx.se/rfc/cookie_spec.html",
        "# This is a generated file!  Do not edit.",
        ""
    ]
    for c in cookies_dict.values():
        exp = c.get("expiration", "0")
        try:
            exp_num = int(float(exp)) if exp else 0
        except (ValueError, TypeError):
            exp_num = 0
            
        if exp_num <= now_ts:
            exp = default_exp
            
        lines.append(f"{c['domain']}\t{c['flag']}\t{c['path']}\t{c['secure']}\t{exp}\t{c['name']}\t{c['value']}")
    return "\n".join(lines)
