import re

path = r"D:\JOB\DEV\EveryThingDownloader\scratch\fb_story_curl.html"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

print("HTML Length:", len(html))

# 1. Check title tag
title_match = re.search(r'<title[^>]*>(.*?)</title>', html)
if title_match:
    print("Page Title:", title_match.group(1))
else:
    print("Page Title: Not found")

# 2. Check login indicators
print("Contains 'login_form':", "login_form" in html)
print("Contains 'login':", "login" in html.lower())
print("Contains 'c_user':", "c_user" in html)
print("Contains 'xs' (cookie name):", "xs" in html)

# 3. Search for video sources generically
print("\n--- Searching for MP4/Video URLs ---")
video_urls = re.findall(r'(https:[\\/]{2}[^"\'\s]+?\.mp4[^"\'\s]*?)', html)
print(f"Found {len(video_urls)} raw MP4 links.")
for url in video_urls[:5]:
    clean = url.replace("\\/", "/").replace("\\u0025", "%")
    print("  ->", clean[:120])

# 4. Search for photo/image URLs
print("\n--- Searching for image patterns ---")
image_urls = re.findall(r'(https:[\\/]{2}[^"\'\s]+?\.jpg[^"\'\s]*?)', html)
print(f"Found {len(image_urls)} raw JPG links.")
for url in image_urls[:5]:
    clean = url.replace("\\/", "/").replace("\\u0025", "%")
    print("  ->", clean[:120])

# 5. Look for user/uploader profile info
print("\n--- Searching for Joshua (Uploader) ---")
print("Contains 'Joshua':", "Joshua" in html)
print("Contains 'Platillero':", "Platillero" in html)
