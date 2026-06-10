import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
from yt_dlp.networking._curlcffi import CurlCFFIRH
import curl_cffi.requests

# Apply the monkey patch
original_get_request_target = CurlCFFIRH._get_request_target

def custom_get_request_target(self, request):
    ua = request.headers.get('User-Agent', '')
    if ua:
        ua_lower = ua.lower()
        if 'firefox' in ua_lower:
            target_str = 'firefox'
        elif 'safari' in ua_lower and 'chrome' not in ua_lower and 'chromium' not in ua_lower:
            target_str = 'safari'
        elif 'edge' in ua_lower or 'edg/' in ua_lower:
            target_str = 'edge'
        elif 'android' in ua_lower:
            target_str = 'chrome-131:android-14'
        else:
            target_str = 'chrome'
        try:
            resolved = self._resolve_target(ImpersonateTarget.from_str(target_str))
            if resolved:
                print(f"[Trace] Mapped User-Agent '{ua[:50]}...' to target: {resolved}")
                return resolved
        except Exception as e:
            print(f"[Trace] Failed resolving target for '{target_str}': {e}")
    return original_get_request_target(self, request)

CurlCFFIRH._get_request_target = custom_get_request_target

url = "https://www.youtube.com/watch?v=eBm23CzA-w4"

# Intercept session.request to inspect final arguments
original_request = curl_cffi.requests.Session.request

def custom_session_request(self, method, url, **kwargs):
    print(f"\n[curl_cffi Request]")
    print(f"  URL: {url}")
    print(f"  Impersonate target: {kwargs.get('impersonate')}")
    print(f"  Headers:")
    for k, v in kwargs.get('headers', {}).items():
        print(f"    {k}: {v}")
    return original_request(self, method, url, **kwargs)

curl_cffi.requests.Session.request = custom_session_request

ydl_opts = {
    "quiet": True,
    "no_warnings": False,
    "nocheckcertificate": True,
    "noplaylist": True,
    "impersonate": ImpersonateTarget.from_str("chrome"),
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.extract_info(url, download=False)
