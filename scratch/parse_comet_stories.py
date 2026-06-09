import re
import json
import urllib.parse

html_path = "d:/JOB/DEV/EveryThingDownloader/scratch/story.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Find all JSON script blocks
scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)

stories_list = []

# Recursively search for keys 'unified_stories' or 'unified_stories_with_notes' or story bucket owner
# Let's search inside all scripts
for idx, script in enumerate(scripts):
    try:
        data = json.loads(script)
        
        # We want to find any object that has 'unified_stories' or 'unified_stories_with_notes'
        # Let's search recursively
        def search_for_buckets(d):
            if isinstance(d, dict):
                # Check if it has unified_stories
                for k in ['unified_stories', 'unified_stories_with_notes']:
                    if k in d and isinstance(d[k], dict) and 'edges' in d[k]:
                        edges = d[k]['edges']
                        if edges:
                            bucket_id = d.get('id')
                            owner = d.get('story_bucket_owner') or d.get('owner')
                            owner_name = owner.get('name') if isinstance(owner, dict) else "Unknown"
                            print(f"Found story bucket! ID: {bucket_id}, Owner: {owner_name}, Stories count: {len(edges)}")
                            
                            # Parse each story card node
                            for edge_idx, edge in enumerate(edges):
                                node = edge.get('node')
                                if not isinstance(node, dict):
                                    continue
                                card_id = node.get('id')
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
                                    preferred_thumbnail = media.get('preferred_thumbnail')
                                    thumbnail_uri = None
                                    if isinstance(preferred_thumbnail, dict):
                                        img = preferred_thumbnail.get('image')
                                        if isinstance(img, dict):
                                            thumbnail_uri = img.get('uri')
                                            
                                    print(f"  Story {edge_idx+1}: ID={card_id}, Type={typename}, MediaID={media_id}")
                                    if playable_url:
                                        print(f"    playable_url: {playable_url[:80]}...")
                                    if thumbnail_uri:
                                        print(f"    thumbnail_uri: {thumbnail_uri[:80]}...")
                                        
                                    stories_list.append({
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
                    
        search_for_buckets(data)
    except Exception as e:
        pass

print(f"\nTotal parsed stories from JSON: {len(stories_list)}")
