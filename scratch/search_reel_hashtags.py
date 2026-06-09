import codecs
import re

path = "scratch/fb_reel_mobile.html"
with codecs.open(path, encoding='utf-16') as f:
    html = f.read()

hashtag = "angiquaynay"
positions = [m.start() for m in re.finditer(hashtag, html)]
print(f"Found hashtag at positions: {positions}")

for idx, pos in enumerate(positions):
    print(f"\n--- Occurrence {idx+1} (pos: {pos}) ---")
    start = max(0, pos - 1500)
    end = min(len(html), pos + 1500)
    snippet = html[start:end]
    print(snippet[:800] + " ... [TRUNCATED] ... " + snippet[-800:])
    
    # Search for numeric values or keys related to feedback, likes, reactions, shares, comments
    sub_matches = re.findall(r'("\w*(?:like|reaction|count|feedback|comment|share|view|like_count|reaction_count)\w*"\s*:\s*(?:[^,{}"]+|"[^"]*"))', snippet, re.IGNORECASE)
    print("\nRelated properties in this snippet:")
    for m in sub_matches:
        print(" ", m)
