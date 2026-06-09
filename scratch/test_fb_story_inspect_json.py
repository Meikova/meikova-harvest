import re
import json

path = r"D:\JOB\DEV\EveryThingDownloader\scratch\fb_story_curl.html"

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

# Find occurrences of 'Joshua' or 'Platillero' and print the surrounding 2000 characters
print("--- Looking for Joshua Platillero surrounding context ---")
for m in re.finditer(r'Joshua\s+Platillero', html):
    start = max(0, m.start() - 500)
    end = min(len(html), m.end() + 2000)
    snippet = html[start:end]
    print(f"Match found at position {m.start()}:\n")
    print(snippet)
    print("\n" + "="*80 + "\n")
