import subprocess
import os
import re

cookies_file = r"D:\JOB\DEV\EveryThingDownloader\downloads\cookies\cookies_client_537ngrlf0hnuty574auzds.txt"
url = "https://www.facebook.com/stories/729012027223830/UzpfSVNDOjE1MzIxMzM0MDE4MzY2Mzc=/?bucket_count=9&source=story_tray"

if not os.path.exists(cookies_file):
    print("Error: Cookies file not found.")
    exit(1)

print("Running curl request to Facebook...")
command = [
    "curl",
    "-s",
    "-L",
    "-b", cookies_file,
    "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "-H", "Accept-Language: vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "-H", "Sec-Fetch-Mode: navigate",
    "-H", "Upgrade-Insecure-Requests: 1",
    url
]

try:
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    html = result.stdout
    print("Curl exited with code:", result.returncode)
    print("HTML Length:", len(html))
    
    # Save output for inspection
    output_path = r"D:\JOB\DEV\EveryThingDownloader\scratch\fb_story_curl.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved HTML to", output_path)
    
    if "Sorry, something went wrong" in html:
        print("Facebook blocked the request (Sorry, something went wrong page).")
    elif "login.php" in html or "login_form" in html:
        print("Facebook redirected/showed login form. Session might be invalid.")
    else:
        print("Success? Let's check for video patterns...")
        matches = re.findall(r'"playable_url"\s*:\s*"([^"]+)"', html)
        print("Playable URLs found:", len(matches))
        for m in matches[:3]:
            print("  ->", m.replace("\\/", "/")[:120])
            
        hd_matches = re.findall(r'"playable_url_quality_hd"\s*:\s*"([^"]+)"', html)
        print("HD Playable URLs found:", len(hd_matches))
        for m in hd_matches[:3]:
            print("  ->", m.replace("\\/", "/")[:120])
            
except Exception as e:
    print("Error executing curl:", e)
