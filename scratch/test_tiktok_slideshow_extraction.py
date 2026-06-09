import sys
import os

# Add parent directory to path so we can import from app.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import extract_tiktok_slideshow_via_gallery_dl

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

url = "https://www.tiktok.com/@mi3k_18dp/video/7649036378268781842"
client_id = "client_537ngrlf0hnuty574auzds"

print(f"Testing extract_tiktok_slideshow_via_gallery_dl for {url}...")
try:
    result = extract_tiktok_slideshow_via_gallery_dl(url, client_id)
    if result:
        print("SUCCESS!")
        print("Keys in result:", list(result.keys()))
        print("Title:", result.get("title"))
        print("Uploader:", result.get("uploader"))
        print("Platform Class:", result.get("platform_class"))
        print("Likes:", result.get("likes"))
        print("Views:", result.get("views"))
        print("Images Count:", len(result.get("images", [])))
        print("Video Options Count:", len(result.get("video_options", [])))
        print("Audio Options Count:", len(result.get("audio_options", [])))
        
        # Print first few image items
        if result.get("images"):
            print("First 3 Images:")
            for img in result.get("images")[:3]:
                print(f"  - Label: {img.get('label')} | Url: {img.get('url')[:100]}...")
                
        # Print audio options
        if result.get("audio_options"):
            print("Audio Options:")
            for opt in result.get("audio_options"):
                print(f"  - Format: {opt.get('format_id')} | Label: {opt.get('label')} | Size: {opt.get('size')} | Url: {opt.get('url')[:100]}...")
    else:
        print("FAILED: Result is None")
except Exception as e:
    print("FAILED with exception:", e)
