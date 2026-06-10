import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_ydl_instance, ImpersonateTarget

url = "https://www.youtube.com/watch?v=eBm23CzA-w4"

print("ImpersonateTarget loaded:", ImpersonateTarget)

ydl_opts = {
    "quiet": True,
    "no_warnings": False,
    "nocheckcertificate": True,
    "noplaylist": True,
}

print("Before create_ydl_instance:", ydl_opts)

try:
    ydl = create_ydl_instance(ydl_opts, url)
    print("After create_ydl_instance:", ydl_opts)
    
    # Let's verify we can extract info
    info = ydl.extract_info(url, download=False)
    print("Success! Extracted info cleanly.")
except Exception as e:
    print("Error during test:", e)
