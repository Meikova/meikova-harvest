import subprocess
import re
import urllib.parse
import os

client_id = "client_537ngrlf0hnuty574auzds"
client_cookies = f"d:/JOB/DEV/EveryThingDownloader/downloads/cookies/cookies_{client_id}.txt"
url = "https://www.facebook.com/stories/729012027223830/UzpfSVNDOjE1MzIxMzM0MDE4MzY2Mzc=/?bucket_count=9&source=story_tray"

command = [
    "curl",
    "-s",
    "-L",
    "-b", client_cookies,
    "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "-H", "Accept-Language: vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "-H", "Sec-Fetch-Mode: navigate",
    "-H", "Upgrade-Insecure-Requests: 1",
    url
]

result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
html = result.stdout
with open("d:/JOB/DEV/EveryThingDownloader/scratch/story.html", "w", encoding="utf-8") as f:
    f.write(html)


print(f"HTML Length: {len(html)}")
if "login.php" in html or "login_form" in html:
    print("Detected redirection to login page!")

# Let's run the regex logic
uploader = "Facebook User"
owner_match = re.search(r'"story_bucket_owner"\s*:\s*{[^}]+?"name"\s*:\s*"([^"]+)"', html)
if owner_match:
    uploader = owner_match.group(1)
else:
    owner_match2 = re.search(r'"owner"\s*:\s*{\s*"name"\s*:\s*"([^"]+)"', html)
    if owner_match2:
        uploader = owner_match2.group(1)

print("Uploader extracted:", uploader)

story_id = None
url_match = re.search(r'/stories/[^/]+/([^//?]+)', url)
if url_match:
    story_id = url_match.group(1)
print("Story ID from URL:", story_id)

raw_playable = re.findall(r'"playable_url"\s*:\s*"([^"]+)"', html)
raw_progressive = re.findall(r'"progressive_url"\s*:\s*"([^"]+)"', html)
print(f"Raw playable: {len(raw_playable)}, Raw progressive: {len(raw_progressive)}")

unique_video_urls = []
for u in raw_playable + raw_progressive:
    clean = u.replace("\\/", "/").replace("\\u0025", "%")
    clean = urllib.parse.unquote(clean)
    if clean not in unique_video_urls and "fbcdn.net" in clean:
        unique_video_urls.append(clean)
print(f"Unique videos: {len(unique_video_urls)}")

raw_photos = re.findall(r'"preferred_thumbnail"\s*:\s*{\s*"image"\s*:\s*{\s*"uri"\s*:\s*"([^"]+)"', html)
raw_photos2 = re.findall(r'"overlay_image_uri"\s*:\s*"([^"]+)"', html)
print(f"Raw preferred_thumbnail: {len(raw_photos)}, Raw overlay_image_uri: {len(raw_photos2)}")

unique_photo_urls = []
for u in raw_photos + raw_photos2:
    clean = u.replace("\\/", "/").replace("\\u0025", "%")
    clean = urllib.parse.unquote(clean)
    if clean not in unique_photo_urls and "fbcdn.net" in clean:
        unique_photo_urls.append(clean)
print(f"Unique photos: {len(unique_photo_urls)}")
