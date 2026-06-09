import re
import json

html_path = "d:/JOB/DEV/EveryThingDownloader/scratch/story.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Let's search for JSON data structures
# Facebook Comet pages use script tags with JSON
scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)

print(f"Total scripts: {len(scripts)}")

story_cards = []
for idx, script in enumerate(scripts):
    if '"stories"' in script or '"story_card"' in script or 'story_cards' in script or 'storyCards' in script or 'unified_stories' in script:
        print(f"Script {idx} contains story indicators (length: {len(script)})")
        
    # Let's look for "story_bucket_owner" or "unified_stories" or "story_cards" or "preferred_thumbnail" or "overlay_image_uri"
    # Facebook uses standard names like CometStorySheetQuery or similar. Let's find comet queries
    # Let's search inside the script for all string keys
    # Let's extract any Comet story card node we can find.
    # In Comet, story cards often have "__typename": "StoryCard" or similar.
    # Let's search for "StoryCard" or "story_card"
    
# Let's write a regex to find Comet store data or GraphQL responses.
# Often there's a JSON block with "require": [...]
# Let's search for Comet story objects in all parsed JSON blocks.
for idx, script in enumerate(scripts):
    try:
        data = json.loads(script)
        # Search recursively for dictionaries with key "story_card" or type "StoryCard"
        found_nodes = []
        def find_nodes(d):
            if isinstance(d, dict):
                typename = d.get("__typename")
                if typename == "StoryCard" or "story_card" in d or "preferred_thumbnail" in d or "playable_url" in d:
                    found_nodes.append(d)
                for k, v in d.items():
                    find_nodes(v)
            elif isinstance(d, list):
                for item in d:
                    find_nodes(item)
        find_nodes(data)
        if found_nodes:
            print(f"Script {idx} has {len(found_nodes)} story-related dicts")
            # Print a few of them
            for n_idx, node in enumerate(found_nodes[:3]):
                keys = list(node.keys())
                print(f"  Node {n_idx+1}: keys={keys}")
                if "id" in node:
                    print(f"    id: {node.get('id')}")
                if "__typename" in node:
                    print(f"    __typename: {node.get('__typename')}")
                if "playable_url" in node:
                    print(f"    playable_url: {node.get('playable_url')[:100]}...")
                if "story_card" in node:
                    print(f"    story_card keys: {list(node.get('story_card').keys()) if isinstance(node.get('story_card'), dict) else type(node.get('story_card'))}")
    except Exception as e:
        pass
