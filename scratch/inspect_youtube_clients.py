import os

ytdlp_dir = "D:\\JOB\\DEV\\EveryThingDownloader\\venv\\Lib\\site-packages\\yt_dlp"
youtube_file = os.path.join(ytdlp_dir, "extractor", "youtube", "_video.py")

with open(youtube_file, "r", encoding="utf-8") as f:
    content = f.read()

# Let's search for client strings like "web", "android", "ios", "mweb", "tv"
lines = content.splitlines()
for idx, line in enumerate(lines):
    if "_clients" in line.lower() or "player_client" in line.lower():
        print(f"{idx+1}: {line.strip()}")
