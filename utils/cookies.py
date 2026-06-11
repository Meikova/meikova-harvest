import json
import logging

logger = logging.getLogger(__name__)

def parse_cookies_to_dict(content):
    """Parses raw cookie content (either JSON or Netscape format) into a structured dictionary."""
    cookies = {}
    stripped = content.strip()
    
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
    """Serializes a dictionary of cookies back into standard Netscape/curl cookiefile format."""
    lines = [
        "# Netscape HTTP Cookie File",
        "# http://curl.haxx.se/rfc/cookie_spec.html",
        "# This is a generated file!  Do not edit.",
        ""
    ]
    for c in cookies_dict.values():
        lines.append(f"{c['domain']}\t{c['flag']}\t{c['path']}\t{c['secure']}\t{c['expiration']}\t{c['name']}\t{c['value']}")
    return "\n".join(lines)
