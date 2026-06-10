import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
import traceback

url = "https://www.youtube.com/watch?v=eBm23CzA-w4"

target = ImpersonateTarget.from_str("chrome")

ydl_opts = {
    "quiet": True,
    "no_warnings": False,
    "nocheckcertificate": True,
    "noplaylist": True,
    "impersonate": target,
}

# Let's inspect the request director handlers when we create a YoutubeDL instance
try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print("Handlers in request director:")
        for name, handler in ydl._request_director.handlers.items():
            print(f"  {name}: {handler} (priority: {getattr(handler, 'priority', 'N/A')})")
        
        info = ydl.extract_info(url, download=False)
        print("Success without explicit backend!")
except Exception as e:
    print(f"Failed with default backend: {e}")
    traceback.print_exc()

print("\n--- Trying with explicit http_backend='curl_cffi' ---")
ydl_opts_cffi = ydl_opts.copy()
ydl_opts_cffi["http_backend"] = "curl_cffi"

try:
    with yt_dlp.YoutubeDL(ydl_opts_cffi) as ydl:
        print("Handlers in request director:")
        for name, handler in ydl._request_director.handlers.items():
            print(f"  {name}: {handler} (priority: {getattr(handler, 'priority', 'N/A')})")
        info = ydl.extract_info(url, download=False)
        print("Success with explicit curl_cffi backend!")
except Exception as e:
    print(f"Failed with explicit curl_cffi backend: {e}")
    traceback.print_exc()
