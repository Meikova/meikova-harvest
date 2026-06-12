"""Comprehensive test of all Facebook URL patterns."""
import sys, os, json, re, logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
import yt_dlp
from config import TEMP_DOWNLOAD_DIR
from utils.ytdl import create_ydl_instance

# All Facebook URL patterns to test
test_urls = [
    # Video/Reel URLs -> should go to yt-dlp
    ("share/v", "https://www.facebook.com/share/v/18fgW8Tbvc/"),
    ("reel", "https://www.facebook.com/reel/769241986206453"),
    ("share/r", "https://www.facebook.com/share/r/1E5vGCgE2Q/"),
    
    # Photo URLs -> should go to custom scraper
    ("share/p", "https://www.facebook.com/share/p/1HuCd4k9ud/"),
    ("posts (photo)", "https://www.facebook.com/DjMie.Official/posts/pfbid036yYFhVafrusuaqygpRhKZR5Abx2BAzQq3wG9Did3NgyxcAzcUEFKQc1n13JxaDeMl"),
]

client_id = "client_lvnnn0l2zy8d6g9idw3j9a"

for label, url in test_urls:
    print(f"\n{'='*60}")
    print(f"[{label}] {url}")
    
    # Determine routing
    is_fb_video_url = any(p in url.lower() for p in ["/share/v/", "/share/r/", "/videos/", "/reel/", "/reels/", "/watch", "fb.watch"])
    route = "yt-dlp" if is_fb_video_url else "custom scraper"
    print(f"  Route: {route}")
    
    if is_fb_video_url:
        # yt-dlp flow
        ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        info = None
        try:
            with create_ydl_instance(ydl_opts, url, client_id) as ydl:
                info = ydl.extract_info(url, download=False)
        except:
            pass
        
        # Quality check
        if info:
            fb_title = (info.get("title") or "").strip().lower()
            fb_thumb = info.get("thumbnail")
            fb_duration = info.get("duration")
            if fb_title in ["facebook", "facebook video", "watch", ""] or (not fb_thumb and not fb_duration):
                print(f"  ⚠️ Cookies gave low quality, retrying...")
                info = None
        
        if not info:
            ydl_opts2 = ydl_opts.copy()
            ydl_opts2.pop("cookiefile", None)
            ydl_opts2.pop("cookiesfrombrowser", None)
            try:
                with yt_dlp.YoutubeDL(ydl_opts2) as ydl2:
                    info = ydl2.extract_info(url, download=False)
            except Exception as e:
                print(f"  ❌ yt-dlp failed: {str(e)[:80]}")
                continue
        
        if info:
            title = info.get("title", "N/A")[:100]
            print(f"  ✅ title: {title}")
            print(f"  ✅ uploader: {info.get('uploader', 'N/A')}")
            print(f"  ✅ thumbnail: {'YES' if info.get('thumbnail') else 'NO'}")
            print(f"  ✅ duration: {info.get('duration')}")
            print(f"  ✅ upload_date: {info.get('upload_date')}")
    else:
        # Custom scraper flow
        from extractors.facebook import scrape_fb_post
        fb_info = scrape_fb_post(url, client_id)
        if fb_info and fb_info.get("status") == "success":
            imgs = fb_info.get("images", [])
            vids = fb_info.get("video_options", [])
            print(f"  ✅ title: {fb_info.get('title', 'N/A')[:100]}")
            print(f"  ✅ uploader: {fb_info.get('uploader', 'N/A')}")
            print(f"  ✅ thumbnail: {'YES' if fb_info.get('thumbnail') else 'NO'}")
            print(f"  ✅ images: {len(imgs)}")
            print(f"  ✅ video_options: {len(vids)}")
        else:
            print(f"  ❌ Custom scraper failed: {fb_info.get('message', 'Unknown')[:80] if fb_info else 'None returned'}")
            print(f"  (This may be due to Facebook rate-limiting this IP)")

print(f"\n{'='*60}")
print("DONE - All patterns tested")
