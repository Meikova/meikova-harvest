"""
Simulate full info.py flow for Facebook reel URL.
This directly imports the route handler's logic to test without restarting server.
"""
import sys, os, json, re, logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

import yt_dlp
from config import TEMP_DOWNLOAD_DIR
from utils.ytdl import create_ydl_instance

url = "https://www.facebook.com/reel/769241986206453"
client_id = "client_lvnnn0l2zy8d6g9idw3j9a"
is_facebook = True

ydl_opts = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
}

print(f"Testing: {url}\n")

# Step 1: Try with cookies (via create_ydl_instance)
info = None
first_err = None
try:
    with create_ydl_instance(ydl_opts, url, client_id) as ydl:
        info = ydl.extract_info(url, download=False)
except Exception as e:
    first_err = e
    logger.warning(f"First attempt failed: {e}")

# Step 2: Quality check for Facebook
if info and is_facebook:
    fb_title = (info.get("title") or "").strip().lower()
    fb_thumb = info.get("thumbnail")
    fb_duration = info.get("duration")
    fb_generic_titles = ["facebook", "facebook video", "watch", ""]
    if fb_title in fb_generic_titles or (not fb_thumb and not fb_duration):
        logger.warning(f"Facebook metadata incomplete (title='{info.get('title')}', thumb={bool(fb_thumb)}, dur={fb_duration}). Retrying...")
        info = None

# Step 3: Retry without cookies
if not info:
    logger.info("Retrying without cookies...")
    ydl_opts_nocookies = ydl_opts.copy()
    ydl_opts_nocookies.pop("cookiefile", None)
    ydl_opts_nocookies.pop("cookiesfrombrowser", None)
    try:
        with yt_dlp.YoutubeDL(ydl_opts_nocookies) as ydl_nocookies:
            info = ydl_nocookies.extract_info(url, download=False)
    except Exception as e:
        logger.error(f"Retry also failed: {e}")

if info:
    title = info.get("title", "Unknown Title")
    uploader = info.get("uploader", "Unknown Channel")
    thumbnail = info.get("thumbnail")
    duration = info.get("duration")
    upload_date = info.get("upload_date")
    view_count = info.get("view_count")
    
    # Facebook title cleanup
    extractor = info.get("extractor_key", "").lower()
    if "facebook" in extractor:
        fb_match = re.match(r"^([\d.,]+[KMB]?) views?\s*·\s*([\d.,]+[KMB]?)\s*reactions?\s*\|\s*(.*)$", title, re.IGNORECASE)
        if fb_match:
            title = fb_match.group(3)
        else:
            fb_match_views = re.match(r"^([\d.,]+[KMB]?) views?\s*\|\s*(.*)$", title, re.IGNORECASE)
            if fb_match_views:
                title = fb_match_views.group(2)
        
        if uploader and uploader != "Unknown Channel":
            title = re.compile(rf"\s*\|\s*{re.escape(uploader)}\s*$", re.IGNORECASE).sub("", title)
    
    # Truncate long title
    if len(title) > 200:
        title = title[:197] + "..."
    
    print(f"\n{'='*60}")
    print(f"FINAL RESULT:")
    print(f"{'='*60}")
    print(f"  title: {title[:150]}")
    print(f"  uploader: {uploader}")
    print(f"  thumbnail: {'YES' if thumbnail else 'NO'}")
    print(f"  duration: {duration}")
    print(f"  upload_date: {upload_date}")
    print(f"  view_count: {view_count}")
    
    formats = info.get("formats", [])
    video_formats = [f for f in formats if f.get("vcodec") != "none" and f.get("vcodec")]
    audio_formats = [f for f in formats if f.get("acodec") != "none" and f.get("acodec") and (f.get("vcodec") == "none" or not f.get("vcodec"))]
    print(f"  video_formats: {len(video_formats)}")
    print(f"  audio_formats: {len(audio_formats)}")
    
    print(f"\n✅ Metadata looks complete!" if (thumbnail and duration and title != "Facebook") else "\n❌ Metadata still incomplete!")
else:
    print("❌ ALL EXTRACTION FAILED!")
