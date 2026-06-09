import re
import urllib.parse

html_path = r"D:\JOB\DEV\EveryThingDownloader\scratch\fb_story_curl.html"
url = "https://www.facebook.com/stories/729012027223830/UzpfSVNDOjE1MzIxMzM0MDE4MzY2Mzc=/?bucket_count=9&source=story_tray"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# 1. Parse URL to get bucket_id and story_id
url_match = re.search(r'/stories/([^/]+)/([^//?]+)', url)
if not url_match:
    print("URL does not match story format.")
    exit(1)

bucket_id = url_match.group(1)
story_id = url_match.group(2)
print(f"Bucket ID: {bucket_id}")
print(f"Story ID: {story_id}")

# 2. Let's find the uploader name in the HTML
owner_match = re.search(r'"owner"\s*:\s*{\s*"name"\s*:\s*"([^"]+)"', html)
uploader = owner_match.group(1) if owner_match else "Facebook User"
print(f"Uploader: {uploader}")

# 3. Locate the story_id in the HTML
pos = html.find(story_id)
if pos == -1:
    print(f"Story ID {story_id} not found in HTML.")
    exit(1)
print(f"Story ID found at position {pos}")

# Let's extract 150,000 characters after the story ID position
segment = html[pos:pos+150000]

# Search for the video ID or media attachments in this segment
# Look for "attachments":[{"media":{"id":"(\d+)","__typename":"Video"
media_match = re.search(r'"media"\s*:\s*{\s*"id"\s*:\s*"(\d+)"\s*,\s*"__typename"\s*:\s*"Video"', segment)
is_video = True
media_id = None
if media_match:
    media_id = media_match.group(1)
    print(f"Found Video Media ID in segment: {media_id}")
else:
    # Try Photo attachment
    photo_match = re.search(r'"media"\s*:\s*{\s*"id"\s*:\s*"(\d+)"\s*,\s*"__typename"\s*:\s*"Photo"', segment)
    if photo_match:
        media_id = photo_match.group(1)
        is_video = False
        print(f"Found Photo Media ID in segment: {media_id}")

if media_id:
    # Search the entire HTML for the video or photo details matching this media_id!
    print(f"\nSearching for media details for ID: {media_id}")
    
    if is_video:
        # Search for progressive_url or playable_url near this media_id (or video_id)
        # In Facebook stories, the video config often has "video_id":"<media_id>"
        # Let's search for the video block in the entire HTML:
        video_pos = html.find(f'"video_id":"{media_id}"')
        if video_pos == -1:
            # Try searching near the media_id generally
            video_pos = html.find(media_id)
            
        if video_pos != -1:
            print(f"Found video_id block at position {video_pos}")
            # Look for progressive_url in the surrounding 5000 characters
            video_segment = html[max(0, video_pos - 3000):video_pos + 1000]
            
            # Find playable_url or progressive_url
            url_match = re.search(r'"playable_url"\s*:\s*"([^"]+)"', video_segment)
            if not url_match:
                url_match = re.search(r'"progressive_url"\s*:\s*"([^"]+)"', video_segment)
                
            if url_match:
                video_url = url_match.group(1).replace("\\/", "/").replace("\\u0025", "%")
                video_url = urllib.parse.unquote(video_url)
                print("SUCCESS! Found Story Video URL:", video_url[:120])
            else:
                print("Could not find playable_url in the video segment.")
        else:
            print("Could not find video_id block in the entire HTML.")
    else:
        # It's a photo, search for the photo URI near this media_id
        photo_pos = html.find(media_id)
        if photo_pos != -1:
            photo_segment = html[photo_pos:photo_pos + 5000]
            url_match = re.search(r'"uri"\s*:\s*"([^"]+)"', photo_segment)
            if url_match:
                photo_url = url_match.group(1).replace("\\/", "/").replace("\\u0025", "%")
                photo_url = urllib.parse.unquote(photo_url)
                print("SUCCESS! Found Story Photo URL:", photo_url[:120])
            else:
                print("Could not find uri in photo segment.")
else:
    print("Could not find media ID in the story ID segment.")
