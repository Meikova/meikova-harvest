"""Test both URL variants after fix."""
import sys, os, json, re, logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
import yt_dlp
from config import TEMP_DOWNLOAD_DIR
from utils.ytdl import create_ydl_instance

urls = [
    "https://www.facebook.com/share/v/18fgW8Tbvc/",
    "https://www.facebook.com/reel/769241986206453",
]

client_id = "client_lvnnn0l2zy8d6g9idw3j9a"

for url in urls:
    print(f"\n{'='*60}")
    print(f"URL: {url}")
    
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
            print(f"  ⚠️ Low quality from cookies, retrying...")
            info = None
    
    if not info:
        ydl_opts2 = ydl_opts.copy()
        ydl_opts2.pop("cookiefile", None)
        ydl_opts2.pop("cookiesfrombrowser", None)
        try:
            with yt_dlp.YoutubeDL(ydl_opts2) as ydl2:
                info = ydl2.extract_info(url, download=False)
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            continue
    
    if info:
        title = info.get("title", "N/A")
        uploader = info.get("uploader", "N/A")
        extractor = info.get("extractor_key", "").lower()
        
        # Clean title
        if "facebook" in extractor:
            m = re.match(r"^([\d.,]+[KMB]?) views?\s*\|\s*(.*)$", title, re.IGNORECASE)
            if m:
                title = m.group(2)
            if uploader and uploader != "Unknown Channel":
                title = re.compile(rf"\s*\|\s*{re.escape(uploader)}\s*$", re.IGNORECASE).sub("", title)
        
        if len(title) > 100:
            title = title[:97] + "..."
        
        thumb = "✅" if info.get("thumbnail") else "❌"
        dur = info.get("duration")
        date = info.get("upload_date")
        
        print(f"  title: {title}")
        print(f"  uploader: {uploader}")
        print(f"  thumbnail: {thumb}")
        print(f"  duration: {dur}")
        print(f"  upload_date: {date}")
        print(f"  {'✅ OK' if dur and info.get('thumbnail') else '❌ INCOMPLETE'}")
