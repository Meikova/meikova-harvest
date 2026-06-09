import codecs
import re
import json

path = "scratch/fb_reel_mobile.html"
with codecs.open(path, encoding='utf-16') as f:
    html = f.read()

print("HTML length:", len(html))

# Look for title tag first
title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
if title_match:
    print("Page Title:", title_match.group(1))

# Let's search for like count or reaction count in the text
# Facebook uses "i18n_reaction_count" or "reaction_count" or "feedback" or "reaction" or "lượt thích"
print("\n--- Search 1: Regex text patterns ---")
patterns = [
    r'([\d.,]+[KMB]?)\s*(?:lượt thích|cảm xúc|thích|likes|reactions)',
    r'(?:likes|reactions|lượt thích|cảm xúc)[:"\s]+([\d.,]+[KMB]?)',
    r'"reaction_count"\s*:\s*(\d+)',
    r'"i18n_reaction_count"\s*:\s*"([^"]+)"',
    r'"like_count"\s*:\s*{\s*"count"\s*:\s*(\d+)',
    r'"i18n_like_count"\s*:\s*"([^"]+)"',
]

for pat in patterns:
    matches = re.findall(pat, html, re.IGNORECASE)
    if matches:
        print(f"Pattern '{pat}': {matches[:10]}")

# Let's search inside the script tags for JSON objects
print("\n--- Search 2: Script tags ---")
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print("Found script tags:", len(scripts))

reaction_keys = ['i18n_reaction_count', 'reaction_count', 'like_count', 'feedback']
found_instances = []
for i, script in enumerate(scripts):
    for key in reaction_keys:
        if key in script:
            print(f"Found '{key}' in script tag {i+1}")
            # Find surrounding text (100 chars)
            pos = script.find(key)
            start = max(0, pos - 150)
            end = min(len(script), pos + 150)
            print(f"Context: ... {script[start:end]} ...")
