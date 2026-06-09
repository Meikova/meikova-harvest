import json
import re

with open("scratch/reel_debug.html", "r", encoding="utf-8") as f:
    html = f.read()

# Find all JSON-like strings in script tags
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"Found {len(scripts)} script tags.")

for idx, script in enumerate(scripts):
    # Search for keys containing 'play' or 'view' followed by numbers
    matches = re.findall(r'["\']([^"\']*(?:play|view|count)[^"\']*)["\']\s*:\s*(\d+|"[^"]+"|\{True|False|null)', script, re.IGNORECASE)
    if matches:
        print(f"\nScript {idx+1} matches:")
        for k, v in list(set(matches))[:20]:
            print(f"  {k}: {v}")
