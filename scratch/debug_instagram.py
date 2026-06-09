import yt_dlp
import os
import sys

def debug_instagram():
    url = "https://www.instagram.com/p/DY4UckRBiTU/?utm_source=ig_web_copy_link&igsh=NTC4MTIwNjQ2YQ=="
    print(f"Debugging Instagram URL: {url}\n")
    
    ydl_opts = {
        "quiet": False,
        "no_warnings": False,
        "nocheckcertificate": True,
        "noplaylist": False,
        "js_runtimes": {"deno": {}, "node": {}, "bun": {}, "quickjs": {}}
    }
    
    # Check if there are active client cookies in downloads/cookies/
    cookies_dir = "downloads/cookies"
    cookies_files = []
    if os.path.exists(cookies_dir):
        cookies_files = [os.path.join(cookies_dir, f) for f in os.listdir(cookies_dir) if f.startswith("cookies_")]
        
    print(f"Found client cookie files: {cookies_files}")
    
    # Test 1: Without cookies
    print("\n--- Test 1: Without cookies ---")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print("Success without cookies!")
            print("Type:", type(info))
            print("Title:", info.get("title"))
    except Exception as e:
        print(f"Failed without cookies: {e}")
        
    # Test 2: With each client cookie file found
    for cf in cookies_files:
        print(f"\n--- Test 2: With cookie file {cf} ---")
        opts = ydl_opts.copy()
        opts["cookiefile"] = cf
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                print(f"Success with cookie file {cf}!")
                print("Title:", info.get("title"))
        except Exception as e:
            print(f"Failed with cookie file {cf}: {e}")

if __name__ == "__main__":
    debug_instagram()
