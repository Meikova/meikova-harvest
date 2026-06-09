import subprocess
import os

client_id = "client_537ngrlf0hnuty574auzds"
cookies_path = f"d:/JOB/DEV/EveryThingDownloader/downloads/cookies/cookies_client_{client_id}.txt"
url = "https://www.facebook.com/stories/729012027223830/UzpfSVNDOjE1MzIxMzM0MDE4MzY2Mzc=/?bucket_count=9&source=story_tray"
output_path = "d:/JOB/DEV/EveryThingDownloader/scratch/story.html"

os.makedirs("d:/JOB/DEV/EveryThingDownloader/scratch", exist_ok=True)

command = [
    "curl",
    "-s",
    "-L",
    "-b", cookies_path,
    "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "-H", "Accept-Language: vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "-H", "Sec-Fetch-Mode: navigate",
    "-H", "Upgrade-Insecure-Requests: 1",
    url
]

print("Running curl command to fetch story...")
result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
html = result.stdout

print(f"Fetched HTML size: {len(html)} characters")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Saved to {output_path}")
