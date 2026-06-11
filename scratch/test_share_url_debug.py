import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from extractors.facebook import scrape_fb_post

test_urls = [
    ("photo", "https://www.facebook.com/photo/?fbid=1000710335659078&set=gm.4436817699935609&idorvanity=3623415467942507"),
    ("share/p", "https://www.facebook.com/share/p/1B9Tkjw1tE/"),
    ("stories", "https://www.facebook.com/stories/1238564336257735/UzpfSVNDOjEyMjQ5NTYwMTk2Mjg4ODQ=/?bucket_count=9&source=story_tray"),
]

client_id = "client_lvnnn0l2zy8d6g9idw3j9a"

for label, url in test_urls:
    print(f"\n==================== {label.upper()} ====================")
    print(f"URL: {url}")
    try:
        res = scrape_fb_post(url, client_id)
        if res and res.get("status") == "success":
            print(f"✅ Status:         {res.get('status')}")
            print(f"✅ Title:          {res.get('title')}")
            print(f"✅ Uploader:       {res.get('uploader')}")
            print(f"✅ Duration:       {res.get('duration')}")
            print(f"✅ Platform Label: {res.get('platform_label')}")
            print(f"✅ Platform Class: {res.get('platform_class')}")
            print(f"✅ Images count:   {len(res.get('images', []))}")
            
            vids = res.get('video_options', [])
            real_vids = [v for v in vids if v.get("ext") == "mp4"]
            photo_vids = [v for v in vids if v.get("ext") == "jpg"]
            print(f"✅ Video Options:  {len(vids)} total ({len(real_vids)} MP4 videos, {len(photo_vids)} JPG photos)")
            
            # Print details of options
            if real_vids:
                print("  --- Real Videos ---")
                for o in real_vids[:3]:
                    print(f"    Label: {o.get('label')}, Res: {o.get('resolution')}, URL: {o.get('url')[:60]}...")
            if photo_vids:
                print("  --- Photo Options ---")
                for o in photo_vids[:3]:
                    print(f"    Label: {o.get('label')}, URL: {o.get('url')[:60]}...")
        else:
            print(f"❌ Custom Scraper failed: {res.get('message') if res else 'None returned'}")
    except Exception as e:
        print(f"❌ Error: {e}")
