import subprocess
import json
import os
import sys

url = "https://www.tiktok.com/@mi3k_18dp/video/7649036378268781842"
cookie_file = "downloads/cookies/cookies_client_537ngrlf0hnuty574auzds.txt"

python_exe = sys.executable
cmd = [python_exe, "-m", "gallery_dl", "-j", url]

if os.path.exists(cookie_file):
    cmd.extend(["--cookies", cookie_file])

print("Running gallery-dl...")
res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")

if res.returncode == 0:
    data = json.loads(res.stdout)
    for element in data:
        if isinstance(element, list) and len(element) >= 2 and element[0] == 2:
            item_data = element[1]
            image_post = item_data.get("imagePost")
            if image_post:
                print("Found imagePost! Keys:", list(image_post.keys()))
                images = image_post.get("images") or []
                print(f"Number of images in imagePost: {len(images)}")
                for idx, img in enumerate(images):
                    print(f"  Image {idx+1}:")
                    # Let's inspect url structures
                    # Usually: displayAddr, ownerWatermarkUserCardAddr, userWatermarkUserCardAddr, thumbnail
                    display_addr = img.get("displayAddr") or (img.get("display_addr") if isinstance(img, dict) else None)
                    print(f"    displayAddr: {display_addr[:100]}..." if display_addr else "    displayAddr: None")
                    # Let's print the entire dictionary keys and first items
                    print(f"    Keys: {list(img.keys())}")
