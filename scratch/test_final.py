import sys, os, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from extractors.facebook import scrape_fb_post

# Test 1: share/v/ video URL
url = "https://www.facebook.com/share/v/18fgW8Tbvc/"
client_id = "client_lvnnn0l2zy8d6g9idw3j9a"
print(f"Testing: {url}")
print("="*60)

result = scrape_fb_post(url, client_id=client_id)

print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"Title: {result.get('title', 'N/A')[:120]}")
    print(f"Uploader: {result.get('uploader', 'N/A')}")
    print(f"Thumbnail: {'YES' if result.get('thumbnail') else 'NO'}")
    
    vo = result.get('video_options', [])
    print(f"\nVideo options ({len(vo)}):")
    for v in vo:
        print(f"  {v['format_id']}: {v['label']} ({v.get('resolution', '?')}) - {v['url'][:80]}...")
    
    imgs = result.get('images', [])
    print(f"\nImages: {len(imgs)}")
else:
    print(f"Error: {result.get('message', 'unknown')}")

# Test 2: Photo post
print("\n" + "="*60)
url2 = "https://www.facebook.com/DjMie.Official/posts/pfbid036yYFhVafrusuaqygpRhKZR5Abx2BAzQq3wG9Did3NgyxcAzcUEFKQc1n13JxaDeMl"
print(f"Testing: {url2[:80]}...")

result2 = scrape_fb_post(url2, client_id=client_id)
print(f"Status: {result2['status']}")
if result2['status'] == 'success':
    print(f"Title: {result2.get('title', 'N/A')[:120]}")
    print(f"Uploader: {result2.get('uploader', 'N/A')}")
    print(f"Video options: {len(result2.get('video_options', []))}")
    print(f"Images: {len(result2.get('images', []))}")
else:
    print(f"Error: {result2.get('message', 'unknown')}")
