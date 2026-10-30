"""Sliding-window rate limiter for Meikova Harvest authentication endpoints.
Follows Meikova Loop loopbox/ratelimit.py architecture.
Zero database overhead, in-memory keyed Blake2b hashing with random per-process salt.
"""
import hashlib
import secrets
import threading
import time
from collections import deque
import os

# Limit configuration: kind -> (requests_allowed, window_seconds, error_message)
LIMITS = {
    "login": (10, 300, "Quá nhiều lần thử đăng nhập. Vui lòng đợi 5 phút."),
    "register": (5, 3600, "Quá nhiều lần đăng ký từ địa chỉ này. Vui lòng thử lại sau."),
    "info": (30, 60, "Quá nhiều yêu cầu phân tích URL. Vui lòng đợi 1 phút."),
    "download": (15, 60, "Quá nhiều yêu cầu khởi tạo tải. Vui lòng đợi 1 phút."),
    "convert": (10, 60, "Quá nhiều yêu cầu chuyển mã media. Vui lòng đợi 1 phút."),
}

PURGE_INTERVAL_S = 300
LOCAL_IPS = {"127.0.0.1", "::1", "localhost"}
TRUSTED_PROXIES = {"127.0.0.1", "::1", "localhost"}

def get_client_ip(request) -> str:
    """Safely extracts client IP address.
    Only trusts X-Forwarded-For or CF-Connecting-IP if the direct connection (remote_addr)
    is from trusted reverse proxies or loopback.
    Otherwise falls back to direct remote_addr to prevent IP spoofing.
    """
    remote_addr = (getattr(request, "remote_addr", None) or "").strip()
    headers = getattr(request, "headers", {})

    if remote_addr in TRUSTED_PROXIES:
        # Check CF-Connecting-IP first (Cloudflare Tunnel)
        cf_ip = headers.get("CF-Connecting-IP")
        if cf_ip and isinstance(cf_ip, str) and cf_ip.strip():
            return cf_ip.strip()

        # Check X-Forwarded-For (Reverse proxy)
        forwarded = headers.get("X-Forwarded-For")
        if forwarded and isinstance(forwarded, str) and forwarded.strip():
            parts = [p.strip() for p in forwarded.split(",") if p.strip()]
            if parts:
                return parts[0]

    return remote_addr or "127.0.0.1"

_lock = threading.Lock()
_hits: dict[tuple[str, str], deque] = {}
_salt = secrets.token_bytes(32)
_last_purge = 0.0

def _get_key(ip: str, kind: str) -> tuple[str, str]:
    masked = hashlib.blake2b(ip.encode("utf-8"), key=_salt, digest_size=12).hexdigest()
    return (masked, kind)

def _purge_expired(now: float) -> None:
    global _last_purge
    if now - _last_purge < PURGE_INTERVAL_S:
        return
    _last_purge = now
    expired_keys = [k for k, q in _hits.items() if not q or now - q[-1] > LIMITS.get(k[1], (10, 300, ""))[1]]
    for k in expired_keys:
        _hits.pop(k, None)

def check_rate_limit(ip: str, kind: str) -> tuple[bool, str]:
    """Checks if request from IP exceeds sliding window limit.
    Returns (True, "") if allowed, or (False, error_message) if rate limited.
    """
    if not ip or ip in LOCAL_IPS:
        return True, ""
    
    if kind not in LIMITS:
        return True, ""
    
    allowed, window, error_msg = LIMITS[kind]
    now = time.time()
    key = _get_key(ip, kind)
    
    with _lock:
        _purge_expired(now)
        q = _hits.setdefault(key, deque())
        while q and (now - q[0] > window):
            q.popleft()
        
        if len(q) >= allowed:
            return False, error_msg
        
        q.append(now)
        return True, ""

def reset_rate_limit(ip: str, kind: str) -> None:
    """Resets rate limit counter upon successful action (e.g. valid login)."""
    if not ip or ip in LOCAL_IPS:
        return
    key = _get_key(ip, kind)
    with _lock:
        _hits.pop(key, None)
