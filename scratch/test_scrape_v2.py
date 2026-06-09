import re
import json
import urllib.parse

html_path = "d:/JOB/DEV/EveryThingDownloader/scratch/story.html"
url = "https://www.facebook.com/stories/729012027223830/UzpfSVNDOjE1MzIxMzM0MDE4MzY2Mzc=/?bucket_count=9&source=story_tray"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

bucket_id = None
story_id = None
url_match = re.search(r'/stories/([^/]+)/([^//?]+)', url)
if url_match:
    bucket_id = url_match.group(1)
    story_id = url_match.group(2)
else:
    url_match2 = re.search(r'/stories/([^//?]+)', url)
    if url_match2:
        bucket_id = url_match2.group(1)

print("Bucket ID:", bucket_id)
print("Story ID:", story_id)

# Try JSON extraction first
parsed_stories = []
context = {'uploader_from_json': None}
scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)

def search_for_buckets(d):
    if isinstance(d, dict):
        for k in ['unified_stories', 'unified_stories_with_notes']:
            if k in d and isinstance(d[k], dict) and 'edges' in d[k]:
                edges = d[k]['edges']
                if edges:
                    current_bucket_id = d.get('id')
                    if bucket_id and str(current_bucket_id) != str(bucket_id):
                        continue
                        
                    owner = d.get('story_bucket_owner') or d.get('owner')
                    if isinstance(owner, dict) and owner.get('name'):
                        context['uploader_from_json'] = owner.get('name')
                        
                    for edge in edges:
                        node = edge.get('node') if isinstance(edge, dict) else None
                        if not isinstance(node, dict):
                            continue
                        card_id = node.get('id')
                        if any(s['card_id'] == card_id for s in parsed_stories):
                            continue
                            
                        attachments = node.get('attachments') or []
                        media = None
                        if attachments and isinstance(attachments, list):
                            att = attachments[0]
                            if isinstance(att, dict):
                                media = att.get('media')
                        if not media and 'media' in node:
                            media = node.get('media')
                            
                        if isinstance(media, dict):
                            typename = media.get('__typename')
                            media_id = media.get('id')
                            playable_url = media.get('playable_url') or media.get('progressive_url')
                            if playable_url:
                                playable_url = playable_url.replace("\\/", "/").replace("\\u0025", "%")
                                playable_url = urllib.parse.unquote(playable_url)
                                
                            thumbnail_uri = None
                            preferred_thumbnail = media.get('preferred_thumbnail')
                            if isinstance(preferred_thumbnail, dict):
                                img = preferred_thumbnail.get('image')
                                if isinstance(img, dict) and img.get('uri'):
                                    thumbnail_uri = img.get('uri')
                            if not thumbnail_uri:
                                img_node = media.get('image') or media.get('previewImage')
                                if isinstance(img_node, dict) and img_node.get('uri'):
                                    thumbnail_uri = img_node.get('uri')
                            
                            if thumbnail_uri:
                                thumbnail_uri = thumbnail_uri.replace("\\/", "/").replace("\\u0025", "%")
                                thumbnail_uri = urllib.parse.unquote(thumbnail_uri)
                                
                            parsed_stories.append({
                                'card_id': card_id,
                                'typename': typename,
                                'media_id': media_id,
                                'playable_url': playable_url,
                                'thumbnail_uri': thumbnail_uri
                            })
        for v in d.values():
            search_for_buckets(v)
    elif isinstance(d, list):
        for item in d:
            search_for_buckets(item)

for script in scripts:
    try:
        data = json.loads(script)
        search_for_buckets(data)
    except Exception:
        pass

print(f"Parsed {len(parsed_stories)} stories from JSON")
print("Uploader from JSON:", context['uploader_from_json'])

video_options = []
if parsed_stories:
    active_story_idx = -1
    for idx, s in enumerate(parsed_stories):
        if story_id and s['card_id'] == story_id:
            active_story_idx = idx
            break
            
    if active_story_idx != -1:
        active_story = parsed_stories.pop(active_story_idx)
        parsed_stories.insert(0, active_story)
        
    video_count = 0
    photo_count = 0
    for idx, s in enumerate(parsed_stories):
        is_active = (story_id and s['card_id'] == story_id) or (idx == 0 and not story_id)
        
        if s['playable_url']:
            video_count += 1
            label = f"Video Story {video_count} (Current)" if is_active else f"Video Story {video_count}"
            video_options.append({
                "format_id": f"direct_video_{idx+1}",
                "ext": "mp4",
                "resolution": "HD" if "quality_hd" in s['playable_url'].lower() else "SD",
                "size": "Unknown Size",
                "label": label,
                "url": s['playable_url']
            })
        elif s['thumbnail_uri']:
            photo_count += 1
            label = f"Photo Story {photo_count} (Current)" if is_active else f"Photo Story {photo_count}"
            video_options.append({
                "format_id": f"direct_photo_{idx+1}",
                "ext": "jpg",
                "resolution": "Original",
                "size": "Unknown Size",
                "label": label,
                "url": s['thumbnail_uri']
            })

print("\n--- EXTRACTED OPTIONS ---")
for opt in video_options:
    print(f"Label: {opt['label']}, Ext: {opt['ext']}, URL: {opt['url'][:80]}...")
