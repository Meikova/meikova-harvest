import re
import json

path = r"D:\JOB\DEV\EveryThingDownloader\scratch\fb_story_curl.html"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

# Search for any URL that looks like fbcdn.net/o1/v/ or similar video CDN url
# and print 100 characters around it to see the JSON key!
print("--- Searching for CDN Video URLs and their JSON keys ---")
# CDN video URLs often contain /o1/v/ or fbcdn.net/v/t2/f2/
matches = re.finditer(r'https:\\\/\\\/[a-z0-9\.-]+\.fbcdn\.net\\\/o1\\\/v\\\/t[0-9]+\\\/f[0-9]+\\\/m[0-9]+\\\/[A-Za-z0-9_-]+', html)

count = 0
for m in matches:
    count += 1
    start = max(0, m.start() - 150)
    end = min(len(html), m.end() + 150)
    snippet = html[start:end]
    print(f"Match {count} at {m.start()}:\n{snippet}\n" + "-"*40)
    if count >= 10:
        break

# Let's search for standard CDN links (without escaped slashes too)
print("\n--- Searching for unescaped video/media links ---")
unescaped_matches = re.finditer(r'https://[a-z0-9\.-]+\.fbcdn\.net/o1/v/[^"\'\s]+', html)
u_count = 0
for m in unescaped_matches:
    u_count += 1
    start = max(0, m.start() - 100)
    end = min(len(html), m.end() + 100)
    snippet = html[start:end]
    print(f"Unescaped Match {u_count} at {m.start()}:\n{snippet}\n" + "-"*40)
    if u_count >= 10:
        break
