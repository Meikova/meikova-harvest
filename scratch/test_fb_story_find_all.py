import re
import urllib.parse

path = r"D:\JOB\DEV\EveryThingDownloader\scratch\fb_story_curl.html"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

# Find uploader name
owner_matches = re.findall(r'"owner"\s*:\s*{\s*"name"\s*:\s*"([^"]+)"', html)
print("Owner names found:", set(owner_matches))

# Find uploader name from another key
actor_matches = re.findall(r'"actor"\s*:\s*{\s*"name"\s*:\s*"([^"]+)"', html)
print("Actor names found:", set(actor_matches))

playable_urls = re.findall(r'"playable_url"\s*:\s*"([^"]+)"', html)
print("\n--- Playable URLs ---")
print(f"Found {len(playable_urls)} playable_url links.")
for idx, url in enumerate(set(playable_urls)):
    clean = url.replace("\\/", "/").replace("\\u0025", "%")
    clean = urllib.parse.unquote(clean)
    print(f" {idx+1}. {clean[:120]}...")

progressive_urls = re.findall(r'"progressive_url"\s*:\s*"([^"]+)"', html)
print("\n--- Progressive URLs ---")
print(f"Found {len(progressive_urls)} progressive_url links.")
for idx, url in enumerate(set(progressive_urls)):
    clean = url.replace("\\/", "/").replace("\\u0025", "%")
    clean = urllib.parse.unquote(clean)
    print(f" {idx+1}. {clean[:120]}...")

preferred_thumbnails = re.findall(r'"preferred_thumbnail"\s*:\s*{\s*"image"\s*:\s*{\s*"uri"\s*:\s*"([^"]+)"', html)
print("\n--- Preferred Thumbnails (Photos) ---")
print(f"Found {len(preferred_thumbnails)} preferred_thumbnail links.")
for idx, url in enumerate(set(preferred_thumbnails)):
    clean = url.replace("\\/", "/").replace("\\u0025", "%")
    clean = urllib.parse.unquote(clean)
    print(f" {idx+1}. {clean[:120]}...")
