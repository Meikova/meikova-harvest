import re

html_path = "d:/JOB/DEV/EveryThingDownloader/scratch/story.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)

script = scripts[13]
print(f"Script 13 length: {len(script)}")
print("\n--- FIRST 2000 CHARACTERS ---")
print(script[:2000])

print("\n--- LAST 2000 CHARACTERS ---")
print(script[-2000:])
