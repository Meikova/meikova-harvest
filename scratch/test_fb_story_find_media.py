import re

path = r"D:\JOB\DEV\EveryThingDownloader\scratch\fb_story_curl.html"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

media_ids = ["1437333751753873", "26992828300328060"]

for mid in media_ids:
    print(f"\n=== Searching for Media ID: {mid} ===")
    for m in re.finditer(mid, html):
        start = max(0, m.start() - 200)
        end = min(len(html), m.end() + 2500)
        print(f"Match at {m.start()}:\n{html[start:end]}\n" + "-"*40)
