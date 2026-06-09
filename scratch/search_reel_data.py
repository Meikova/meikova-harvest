import codecs
import re

path = "scratch/fb_reel_mobile.html"
with codecs.open(path, encoding='utf-16') as f:
    html = f.read()

# Let's find all occurrences of the video ID
id_str = "1263752559080744"
positions = [m.start() for m in re.finditer(id_str, html)]
print(f"Found video ID at positions: {positions}")

for idx, pos in enumerate(positions):
    print(f"\n--- Occurrence {idx+1} (pos: {pos}) ---")
    # Print 2000 characters around the position
    start = max(0, pos - 1000)
    end = min(len(html), pos + 1000)
    snippet = html[start:end]
    print(snippet[:500] + " ... [TRUNCATED] ... " + snippet[-500:])
    
    # Check if we can find any numeric properties representing likes
    # Let's look for "count" or "total" or "reaction" or "like" in the snippet
    sub_matches = re.findall(r'("\w*(?:like|reaction|count|feedback|comment|share|view)\w*"\s*:\s*(?:[^,{}]+))', snippet, re.IGNORECASE)
    print("Related sub-properties in this snippet:", sub_matches)
