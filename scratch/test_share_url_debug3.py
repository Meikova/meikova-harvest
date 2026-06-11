import sys, os, re, json, subprocess, urllib.parse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from config import TEMP_DOWNLOAD_DIR

url = "https://www.facebook.com/share/v/18fgW8Tbvc/"

cookies_dir = os.path.join(TEMP_DOWNLOAD_DIR, "cookies")
cookie_files = [f for f in os.listdir(cookies_dir) if f.startswith("cookies_")]
cookie_file = os.path.join(cookies_dir, cookie_files[0]) if cookie_files else None

command = [
    "curl", "-s", "-L",
    "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "-H", "Accept-Language: vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "-H", "Sec-Fetch-Mode: navigate",
    "-H", "Upgrade-Insecure-Requests: 1",
]
if cookie_file:
    command.extend(["-b", cookie_file])
command.append(url)

result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
html = result.stdout

print(f"HTML length: {len(html)}")

# Strategy 1: Find the permalink/real URL from route info
route_match = re.search(r'/groups/[^/]+/permalink/(\d+)/', html)
if route_match:
    real_post_id = route_match.group(1)
    print(f"Found real post ID from route: {real_post_id}")
else:
    print("No permalink route found")
    
# Strategy 2: Find permalink patterns anywhere
permalink_matches = re.findall(r'/permalink/(\d+)/', html)
print(f"All permalink IDs: {set(permalink_matches)}")

# Strategy 3: Look for video data in the HTML (not just JSON scripts)
# Check for base64 video or blob patterns
video_patterns = [
    (r'"playable_url_quality_hd"\s*:\s*"([^"]+)"', "playable_url_quality_hd"),
    (r'"playable_url"\s*:\s*"([^"]+)"', "playable_url"),
    (r'"progressive_url"\s*:\s*"([^"]+)"', "progressive_url"),
    (r'"browser_native_[sh]d_url"\s*:\s*"([^"]+)"', "browser_native_url"),
    (r'"dash_manifest"\s*:\s*"', "dash_manifest (present)"),
    (r'"video_url"\s*:\s*"([^"]+)"', "video_url"),
]

for pattern, name in video_patterns:
    matches = re.findall(pattern, html)
    if matches:
        print(f"\n{name}: {len(matches)} matches")
        for m in matches[:3]:
            if isinstance(m, str):
                decoded = m.replace("\\/", "/").replace("\\u0025", "%")
                print(f"  {decoded[:150]}...")
    else:
        print(f"{name}: not found")

# Strategy 4: Find video-specific GraphQL types
video_type_matches = re.findall(r'"__typename"\s*:\s*"(Video|VideoStory|VideoDerivativeNode)"', html)
print(f"\nVideo typename matches: {video_type_matches}")

# Strategy 5: Find creation_story or attachments with video
attachment_matches = re.findall(r'"__typename"\s*:\s*"(StoryAttachment|VideoAttachment|MediaAttachment)"', html)
print(f"Attachment typename matches: {attachment_matches}")

# Strategy 6: Look for the "main post" story_fbid or post_fbid
story_fbid = re.findall(r'"story_fbid"\s*:\s*"(\d+)"', html)
print(f"story_fbid values: {set(story_fbid)}")

post_fbid = re.findall(r'"post_id"\s*:\s*"(\d+)"', html)
print(f"post_id values: {set(post_fbid)}")

# Strategy 7: og:video meta tag
og_video = re.search(r'<meta\s+property="og:video(?::url)?"\s+content="([^"]+)"', html)
if og_video:
    print(f"\nog:video: {og_video.group(1)[:200]}")
else:
    print("\nNo og:video meta tag")
    
og_type = re.search(r'<meta\s+property="og:type"\s+content="([^"]+)"', html)
if og_type:
    print(f"og:type: {og_type.group(1)}")
