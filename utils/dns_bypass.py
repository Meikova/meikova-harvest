"""
DNS Bypass Module — Automatically resolves ISP-blocked domains via Google DNS-over-HTTPS.

When Vietnamese ISPs block domains by returning 127.0.0.1 / ::1, this module
transparently resolves them via Google DoH and patches Python's socket.getaddrinfo
so ALL HTTP libraries (requests, curl_cffi, urllib) work without modification.
"""

import socket
import threading
import logging

logger = logging.getLogger(__name__)

# Original getaddrinfo before patching
_original_getaddrinfo = socket.getaddrinfo

# Thread-safe DNS cache
_dns_cache = {}
_dns_lock = threading.Lock()

# Domains currently being resolved (recursion guard)
_resolving = threading.local()

# IPs that indicate ISP DNS blocking
BLOCKED_IPS = {"127.0.0.1", "::1", "0.0.0.0", "localhost", ""}

# Domains used by the DoH resolver itself (must never be re-resolved via DoH)
DOH_INFRA_DOMAINS = {"dns.google", "cloudflare-dns.com", "1.1.1.1", "8.8.8.8", "8.8.4.4"}


def resolve_via_doh(domain):
    """Resolve a domain via Google DNS-over-HTTPS, bypassing ISP DNS blocks."""
    import requests as req
    try:
        resp = req.get(
            f"https://dns.google/resolve?name={domain}&type=A",
            headers={"Accept": "application/dns-json"},
            timeout=5,
            verify=True
        )
        data = resp.json()
        for answer in data.get("Answer", []):
            if answer.get("type") == 1:  # A record
                ip = answer.get("data")
                if ip and ip not in BLOCKED_IPS:
                    return ip
    except Exception as e:
        logger.debug(f"DoH resolution failed for {domain}: {e}")
    return None


def is_local_or_private(host):
    """Checks if a hostname is local, loopback, or private IP, which DoH should ignore."""
    if not host:
        return True
    host_lower = host.lower()
    if host_lower in {"localhost", "0.0.0.0", "127.0.0.1", "::1", "", "none"}:
        return True
    if "." not in host:
        return True
    if host_lower.endswith(".local"):
        return True
    if host.startswith("192.168.") or host.startswith("10."):
        return True
    if host.startswith("172."):
        parts = host.split(".")
        if len(parts) >= 2 and parts[1].isdigit():
            val = int(parts[1])
            if 16 <= val <= 31:
                return True
    return False


def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """Patched socket.getaddrinfo that uses DoH for ISP-blocked domains."""

    # Guard 1: Never intercept local/private hostnames or DoH infrastructure
    if is_local_or_private(host) or host in DOH_INFRA_DOMAINS:
        return _original_getaddrinfo(host, port, family, type, proto, flags)

    # Guard 2: Prevent recursion within the same thread
    if not hasattr(_resolving, "domains"):
        _resolving.domains = set()
    if host in _resolving.domains:
        return _original_getaddrinfo(host, port, family, type, proto, flags)

    # Check cache first
    with _dns_lock:
        cached_ip = _dns_cache.get(host)
    if cached_ip:
        real_port = port if isinstance(port, int) and port else 443
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (cached_ip, real_port))]

    # Try original DNS first
    try:
        results = _original_getaddrinfo(host, port, family, type, proto, flags)
        if results:
            ip = results[0][4][0]
            if ip not in BLOCKED_IPS:
                return results  # Original DNS is fine
            # ISP block detected!
            logger.info(f"ISP DNS block detected for '{host}' (resolved to {ip}). Trying DoH...")
    except socket.gaierror:
        logger.info(f"DNS resolution failed for '{host}'. Trying DoH...")

    # Fallback: resolve via DoH
    _resolving.domains.add(host)
    try:
        real_ip = resolve_via_doh(host)
    finally:
        _resolving.domains.discard(host)

    if real_ip:
        with _dns_lock:
            _dns_cache[host] = real_ip
        logger.info(f"DoH bypass: {host} -> {real_ip}")
        real_port = port if isinstance(port, int) and port else 443
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (real_ip, real_port))]

    # Last resort: let the original error propagate
    return _original_getaddrinfo(host, port, family, type, proto, flags)


def install_dns_bypass():
    """Install the DNS bypass globally. Call once at app startup."""
    socket.getaddrinfo = _patched_getaddrinfo
    logger.info("DNS bypass installed — ISP-blocked domains will be auto-resolved via Google DoH")
