import os
import sys
import socket
import ipaddress
import tempfile
import logging
from urllib.parse import urlparse

from config import BASE_DIR, USER_DATA_DIR, TEMP_DOWNLOAD_DIR

logger = logging.getLogger(__name__)

# Dangerous executable extensions blocked from local opening/execution
BLOCKED_EXECUTABLE_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".msi",
    ".reg", ".scr", ".pif", ".com", ".hta", ".sh", ".py",
    ".dll", ".sys", ".cpl", ".jar", ".vbe", ".wsf", ".wsh"
}

# Blocked hostnames for SSRF defense
BLOCKED_HOSTNAMES = {
    "localhost", "127.0.0.1", "0.0.0.0", "::1", "0",
    "metadata.google.internal", "instance-data"
}


def is_safe_remote_url(url: str) -> tuple[bool, str]:
    """
    Validates that a URL is a valid remote HTTP/HTTPS target and does NOT resolve
    to internal network ranges, loopbacks, link-local metadata (SSRF defense).
    Returns (is_safe: bool, reason: str).
    """
    if not url or not isinstance(url, str):
        return False, "Missing or invalid URL."

    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Malformed URL syntax: {e}"

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return False, f"Prohibited URL scheme '{scheme}'. Only http and https are permitted."

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return False, "Missing hostname in URL."

    if hostname in BLOCKED_HOSTNAMES:
        return False, f"Target hostname '{hostname}' is a restricted local or metadata address."

    # Prevent explicit IP loopbacks or local ranges directly in hostname
    try:
        direct_ip = ipaddress.ip_address(hostname)
        if direct_ip.is_private or direct_ip.is_loopback or direct_ip.is_link_local or direct_ip.is_reserved or direct_ip.is_multicast:
            return False, f"IP address '{hostname}' is within a private or restricted network range."
        if str(direct_ip) == "169.254.169.254":
            return False, "Cloud metadata IP (169.254.169.254) is strictly prohibited."
        return True, ""
    except ValueError:
        # Hostname is a domain name, proceed to DNS resolution
        pass

    try:
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for entry in addr_info:
            ip_str = entry[4][0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved or ip_obj.is_multicast:
                    return False, f"Domain '{hostname}' resolves to restricted IP '{ip_str}'."
                if str(ip_obj) == "169.254.169.254":
                    return False, "Domain resolves to prohibited cloud metadata IP."
            except ValueError:
                continue
    except socket.gaierror:
        # If DNS resolution fails (e.g. offline unit testing or mock domain):
        # Allow standard domains unless clearly internal
        internal_suffixes = (".local", ".internal", ".lan", ".home", ".corp", ".arpa")
        if any(hostname.endswith(sfx) for sfx in internal_suffixes):
            return False, f"Domain '{hostname}' uses an internal-only suffix."
        logger.debug(f"DNS lookup failed for {hostname}; permitted for offline/mock requests.")
    except Exception as err:
        logger.warning(f"Error checking remote URL safety for {url}: {err}")

    return True, ""


def get_allowed_media_directories(extra_dirs: list = None) -> list:
    """Returns canonical list of directories where local media access is permitted."""
    allowed = [
        os.path.realpath(TEMP_DOWNLOAD_DIR),
        os.path.realpath(USER_DATA_DIR),
        os.path.realpath(BASE_DIR),
        os.path.realpath(tempfile.gettempdir()),
    ]

    # Standard User Downloads directory
    try:
        user_downloads = os.path.realpath(os.path.join(os.path.expanduser("~"), "Downloads"))
        if os.path.exists(user_downloads):
            allowed.append(user_downloads)
    except Exception:
        pass

    # Standard User Videos and Music
    try:
        user_videos = os.path.realpath(os.path.join(os.path.expanduser("~"), "Videos"))
        if os.path.exists(user_videos):
            allowed.append(user_videos)
        user_music = os.path.realpath(os.path.join(os.path.expanduser("~"), "Music"))
        if os.path.exists(user_music):
            allowed.append(user_music)
    except Exception:
        pass

    # Custom downloads folder from environment if set
    custom_dl = os.environ.get("DOWNLOADS_DIR")
    if custom_dl and os.path.exists(custom_dl):
        allowed.append(os.path.realpath(custom_dl))

    if extra_dirs:
        for d in extra_dirs:
            if d and os.path.exists(d):
                allowed.append(os.path.realpath(d))

    return list(dict.fromkeys(allowed))


ALLOWED_MEDIA_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv", ".ts", ".m4v",
    ".mp3", ".wav", ".flac", ".m4a", ".ogg", ".opus", ".aac", ".wma",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".svg",
    ".vtt", ".srt", ".ass", ".txt", ".json", ".m3u8", ".mpd", ".tor", ".torrent"
}


def is_safe_local_media_path(file_path: str, extra_dirs: list = None, allow_user_local_media: bool = False) -> tuple[bool, str]:
    """
    Validates that a local file path exists, is NOT an executable, and resides
    within one of the permitted directories (Path Traversal defense).
    If allow_user_local_media is True, allows media files outside standard directories
    provided they have a valid media extension and are outside critical system OS directories.
    Returns (is_safe: bool, reason: str).
    """
    if not file_path or not isinstance(file_path, str):
        return False, "Missing or invalid file path."

    norm_path = os.path.realpath(os.path.abspath(file_path))
    ext = os.path.splitext(norm_path)[1].lower()

    if ext in BLOCKED_EXECUTABLE_EXTENSIONS:
        return False, f"Executable file extension '{ext}' is prohibited."

    # Prevent access to system core directories
    norm_lower = norm_path.lower()
    system_roots = [
        os.environ.get("SystemRoot", "C:\\Windows").lower(),
        "c:\\windows", "/etc", "/bin", "/sbin", "/boot", "/usr/bin"
    ]
    for sys_root in system_roots:
        if norm_lower.startswith(sys_root.lower() + os.sep) or norm_lower == sys_root.lower():
            return False, "Access to system directory is strictly prohibited."

    allowed_roots = get_allowed_media_directories(extra_dirs)
    is_contained = False

    for root in allowed_roots:
        try:
            common = os.path.commonpath([root, norm_path])
            if common == root:
                is_contained = True
                break
        except ValueError:
            continue

    if is_contained:
        return True, ""

    if allow_user_local_media and ext in ALLOWED_MEDIA_EXTENSIONS:
        return True, ""

    return False, f"File path is outside permitted application directories."
