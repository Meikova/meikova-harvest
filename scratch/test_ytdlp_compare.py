"""Compare yt-dlp output for the same video via different URLs."""
import sys, os, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import yt_dlp
from config import TEMP_DOWNLOAD_DIR

urls = [
    "https://www.facebook.com/share/v/18fgW8Tbvc/",
    "https://www.facebook.com/reel/769241986206453",
]

cookie_file = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", "cookies_client_lvnnn0l2zy8d6g9idw3j9a.txt")

for url in urls:
    print(f"\n{'='*60}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    
    info = None
    # Try without cookies first (since cookies are causing issues)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        print(f"  Error: {e}")
        continue
    
    if info:
        # Print key metadata fields
        keys = ["id", "title", "description", "uploader", "uploader_id", "channel",
                "thumbnail", "duration", "upload_date", "view_count", "like_count",
                "webpage_url", "original_url", "extractor", "extractor_key",
                "width", "height"]
        for k in keys:
            v = info.get(k)
            if v is not None:
                if isinstance(v, str) and len(v) > 120:
                    v = v[:120] + "..."
                print(f"  {k}: {v}")
        
        # Print format list
        formats = info.get("formats", [])
        print(f"\n  Formats ({len(formats)}):")
        for f in formats:
            fid = f.get("format_id", "?")
            ext = f.get("ext", "?")
            w = f.get("width", "?")
            h = f.get("height", "?")
            fs = f.get("filesize") or f.get("filesize_approx")
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            print(f"    {fid}: {ext} {w}x{h} vcodec={vcodec} acodec={acodec} size={fs}")
