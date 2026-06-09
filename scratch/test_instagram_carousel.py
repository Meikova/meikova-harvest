import yt_dlp
import os
import sys

def test_instagram_carousel():
    url = "https://www.instagram.com/p/Cw9p1o_I0W1/"  # Public post
    print(f"Testing extraction for Instagram URL: {url}")
    
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "noplaylist": False,  # Allow carousel entries
    }
    
    # Try using browser cookies fallback if available
    browsers = ["chrome", "edge", "firefox"]
    ydl = None
    for browser in browsers:
        opts = ydl_opts.copy()
        opts["cookiesfrombrowser"] = (browser,)
        try:
            ydl = yt_dlp.YoutubeDL(opts)
            # Try to load cookies to see if they exist
            _ = ydl.cookiejar
            print(f"Successfully loaded cookies from browser: {browser}")
            break
        except Exception:
            pass
            
    if not ydl:
        print("No browser cookies loaded. Falling back to default instance.")
        ydl = yt_dlp.YoutubeDL(ydl_opts)
        
    try:
        info = ydl.extract_info(url, download=False)
        if not info:
            print("Failed: No info extracted.")
            return
            
        print("Success!")
        print(f"Title: {info.get('title')}")
        print(f"Uploader: {info.get('uploader')}")
        print(f"Extractor: {info.get('extractor_key')}")
        
        entries = info.get("entries") or []
        print(f"Number of Carousel entries: {len(entries)}")
        for idx, entry in enumerate(entries):
            print(f"Entry {idx+1}:")
            print(f"  Title: {entry.get('title')}")
            print(f"  Formats: {len(entry.get('formats', []))} formats found.")
            print(f"  URL/Thumbnail: {entry.get('url') or entry.get('thumbnail')}")
            
    except Exception as e:
        print(f"Failed to extract info: {e}")
        err_msg = str(e).lower()
        if any(keyword in err_msg for keyword in ["login", "redirect", "challenge", "checkpoint"]):
            print("-> Successfully detected Instagram authentication/cookie wall restriction.")

if __name__ == "__main__":
    test_instagram_carousel()
