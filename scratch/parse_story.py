import re
import json
import urllib.parse

html_path = "d:/JOB/DEV/EveryThingDownloader/scratch/story.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

print("File size:", len(html))

# Let's find all script blocks containing JSON data
scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
print(f"Found {len(scripts)} application/json script blocks")

# Let's search inside each script block for story related data
story_data_found = False

# We can search the raw HTML for some story keywords
print("\n--- Raw Keyword Searches ---")
for kw in ['story_bucket_owner', 'story_card', 'storyCard', 'unified_stories', 'story_bucket', 'preferred_thumbnail']:
    matches = list(re.finditer(kw, html))
    print(f"Keyword '{kw}': {len(matches)} matches")

# Let's search for "storyCard" or similar in application/json scripts
for idx, script in enumerate(scripts):
    if 'story' in script or 'unified_stories' in script or 'preferred_thumbnail' in script:
        print(f"\nScript {idx} length: {len(script)} contains 'story' or 'unified_stories' or 'preferred_thumbnail'")
        # Try to parse as JSON
        try:
            data = json.loads(script)
            # Dump a small part or search keys
            def search_keys(d, path=""):
                if isinstance(d, dict):
                    for k, v in d.items():
                        new_path = f"{path}.{k}" if path else k
                        if k in ['unified_stories', 'story_bucket', 'story_card', 'story_cards', 'storyCards', 'story_bucket_owner', 'nodes', 'edges']:
                            print(f"Found key: {new_path} (Type: {type(v)})")
                        search_keys(v, new_path)
                elif isinstance(d, list):
                    for i, item in enumerate(d):
                        search_keys(item, f"{path}[{i}]")
            
            search_keys(data)
        except Exception as e:
            # Maybe it is not valid JSON or has trailing issues
            print(f"Could not parse script {idx} as JSON: {e}")

# Let's look for matching blocks of story cards manually
print("\n--- Extracting Story Card JSON blocks ---")
# Story cards are usually represented by dictionaries having "story_card" or similar keys
# Let's find all occurrences of "story_bucket_owner" and extract surrounding text
matches = [m.start() for m in re.finditer(r'"story_bucket_owner"', html)]
for idx, pos in enumerate(matches):
    start = max(0, pos - 1000)
    end = min(len(html), pos + 10000)
    snippet = html[pos:pos+200]
    print(f"Match {idx} at position {pos}: {snippet}...")
