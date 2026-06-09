import re

with open("scratch/reel_debug.html", "r", encoding="utf-8") as f:
    html = f.read()

print("Searching for 'play' in HTML...")
play_matches = list(re.finditer(r'play', html, re.IGNORECASE))
print(f"Total 'play' occurrences: {len(play_matches)}")
for m in play_matches[:15]:
    start = max(0, m.start() - 50)
    end = min(len(html), m.end() + 50)
    print("  MATCH:", repr(html[start:end]))

print("\nSearching for 'view' in HTML...")
view_matches = list(re.finditer(r'view', html, re.IGNORECASE))
print(f"Total 'view' occurrences: {len(view_matches)}")
for m in view_matches[:15]:
    start = max(0, m.start() - 50)
    end = min(len(html), m.end() + 50)
    print("  MATCH:", repr(html[start:end]))
