import re
import urllib.parse

html_path = "d:/JOB/DEV/EveryThingDownloader/scratch/story.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

raw_playable = re.findall(r'"playable_url"\s*:\s*"([^"]+)"', html)
raw_progressive = re.findall(r'"progressive_url"\s*:\s*"([^"]+)"', html)

print("--- PLAYABLE / PROGRESSIVE VIDEO URLS ---")
for idx, u in enumerate(raw_playable + raw_progressive):
    clean = u.replace("\\/", "/").replace("\\u0025", "%")
    clean = urllib.parse.unquote(clean)
    if "fbcdn.net" in clean:
        print(f"\nURL {idx+1}:")
        print("Cleaned URL:", clean[:150] + "...")
        # Check URL parameters for story id or media id or quality
        # Try to find indicators like aspect ratio, dimensions, or IDs
        params = urllib.parse.parse_qs(urllib.parse.urlparse(clean).query)
        for k, v in params.items():
            if k in ['_nc_vs', 'bitrate', 'tag', 'quality_hd', 'bytestart', 'byteend', 'oh', 'oe']:
                print(f"  {k}: {v}")

print("\n--- PHOTO URLS ---")
raw_photos = re.findall(r'"preferred_thumbnail"\s*:\s*{\s*"image"\s*:\s*{\s*"uri"\s*:\s*"([^"]+)"', html)
raw_photos2 = re.findall(r'"overlay_image_uri"\s*:\s*"([^"]+)"', html)

for idx, u in enumerate(raw_photos + raw_photos2):
    clean = u.replace("\\/", "/").replace("\\u0025", "%")
    clean = urllib.parse.unquote(clean)
    if "fbcdn.net" in clean:
        print(f"\nPhoto {idx+1}:")
        print("Cleaned Photo URL:", clean[:150] + "...")
