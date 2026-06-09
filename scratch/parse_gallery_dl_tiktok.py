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
    try:
        data = json.loads(res.stdout)
        print("Successfully parsed gallery-dl JSON!")
        # gallery-dl JSON output is usually a list of [type, data] elements
        # Let's inspect them
        print(f"Number of elements: {len(data)}")
        
        # Let's find image URLs
        images = []
        for element in data:
            if isinstance(element, list) and len(element) >= 2:
                # Type 3 represents actual download items (usually the files/urls)
                item_type = element[0]
                item_data = element[1]
                if item_type == 3:
                    # This is the download URL
                    images.append(item_data)
                elif item_type == 2:
                    # This is metadata block
                    print("Found metadata block! Keys:", list(item_data.keys()))
                    if "imagePostInfo" in item_data:
                        print("Found imagePostInfo!")
                        img_info = item_data["imagePostInfo"]
                        print("imagePostInfo keys:", list(img_info.keys()))
                        if "images" in img_info:
                            for idx, img in enumerate(img_info["images"]):
                                print(f"Slide Image {idx+1} keys:", list(img.keys()))
                                # Let's find URL
                                display_url = img.get("displayAddr") or (img.get("display_addr") if isinstance(img, dict) else None)
                                print(f"  displayAddr: {display_url}")
                    # Let's also check for 'images' key in standard metadata
                    if "images" in item_data:
                        print("Found images in metadata!", len(item_data["images"]))
        
        print(f"\nExtracted {len(images)} URLs of type 3:")
        for idx, img_url in enumerate(images):
            print(f" - Item {idx+1}: {img_url[:120]}...")
            
    except Exception as e:
        print("Failed to parse JSON:", e)
else:
    print("gallery-dl failed:", res.stderr)
