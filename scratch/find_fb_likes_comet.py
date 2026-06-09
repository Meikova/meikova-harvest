import re
import os

dump_file = "1263752559080744_https_-_www.facebook.com_watch_v=1263752559080744__rdr.dump"
with open(dump_file, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

pos = content.find('"video_view_count":240529')
if pos != -1:
    print("Found video_view_count at:", pos)
    # Search for "reaction_count" or "i18n_reaction_count" after pos
    search_area = content[pos:pos+50000]
    
    # Find all occurrences of reaction_count
    for m in re.finditer(r'"(i18n_reaction_count|reaction_count)"\s*:\s*([^,}]+)', search_area):
        print(f"Match: {m.group(0)} at relative pos {m.start()}")
        # Print surrounding context
        start = max(0, m.start() - 100)
        end = min(len(search_area), m.start() + 200)
        print("Context:", search_area[start:end])
        print("-" * 50)
else:
    print("video_view_count not found.")
