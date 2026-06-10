import yt_dlp
import sys

print("Python version:", sys.version)
print("yt-dlp version:", yt_dlp.version.__version__)

url = "https://www.youtube.com/watch?v=eBm23CzA-w4"

# Let's test with different impersonate settings
impersonate_options = ["chrome", "chrome-110", "chrome:windows-110", "chrome:windows"]

for opt in impersonate_options:
    print(f"\n--- Testing impersonate: {opt} ---")
    ydl_opts = {
        "quiet": True,
        "no_warnings": False,
        "nocheckcertificate": True,
        "noplaylist": True,
        "impersonate": opt,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(f"Success! Title: {info.get('title')}")
            break
    except Exception as e:
        print(f"Failed with impersonate={opt}: {e}")
