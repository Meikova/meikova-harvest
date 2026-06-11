import sys, os, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from extractors.facebook import scrape_fb_post

# Test 1: share/v/ URL (video)
print("="*60)
print("TEST 1: share/v/ URL (video)")
print("="*60)
url1 = "https://www.facebook.com/share/v/18fgW8Tbvc/"
r1 = scrape_fb_post(url1, client_id="client_lvnnn0l2zy8d6g9idw3j9a")
print(f"Status: {r1['status']}")
print(f"Videos: {len(r1.get('video_options', []))}")
for vo in r1.get('video_options', []):
    print(f"  {vo['format_id']}: {vo['label']}")
print(f"Images: {len(r1.get('images', []))}")

# Test 2: Photo post (DjMie)
print("\n" + "="*60)
print("TEST 2: Photo post (DjMie)")
print("="*60)
url2 = "https://www.facebook.com/DjMie.Official/posts/pfbid036yYFhVafrusuaqygpRhKZR5Abx2BAzQq3wG9Did3NgyxcAzcUEFKQc1n13JxaDeMl?rdid=LV7jEAcmGyFlYW0H"
r2 = scrape_fb_post(url2, client_id="client_lvnnn0l2zy8d6g9idw3j9a")
print(f"Status: {r2['status']}")
print(f"Videos: {len(r2.get('video_options', []))}")
for vo in r2.get('video_options', []):
    if 'photo' in vo['format_id']:
        print(f"  {vo['format_id']}: {vo['label']}")
    else:
        print(f"  {vo['format_id']}: {vo['label']}")
print(f"Images: {len(r2.get('images', []))}")

# Test 3: share/p/ URL (photo) 
print("\n" + "="*60)
print("TEST 3: share/p/ URL (photo)")
print("="*60)
url3 = "https://www.facebook.com/share/p/1HuCd4k9ud/"
r3 = scrape_fb_post(url3, client_id="client_lvnnn0l2zy8d6g9idw3j9a")
print(f"Status: {r3['status']}")
print(f"Videos: {len(r3.get('video_options', []))}")
for vo in r3.get('video_options', []):
    print(f"  {vo['format_id']}: {vo['label']}")
print(f"Images: {len(r3.get('images', []))}")
