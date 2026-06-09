import re
import urllib.parse

html_path = "d:/JOB/DEV/EveryThingDownloader/scratch/story.html"
story_id = "UzpfSVNDOjE1MzIxMzM0MDE4MzY2Mzc="

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Let's search for the story ID
pos = html.find(story_id)
if pos == -1:
    print("Story ID not found in HTML!")
else:
    print(f"Found story ID at position {pos}")
    # Print multiple snippets around it (since it might occur multiple times)
    occurrences = [m.start() for m in re.finditer(re.escape(story_id), html)]
    print(f"Total occurrences: {len(occurrences)}")
    for i, occ in enumerate(occurrences):
        print(f"\n--- OCCURRENCE {i+1} at {occ} ---")
        start = max(0, occ - 1000)
        end = min(len(html), occ + 1000)
        print(html[start:end])
