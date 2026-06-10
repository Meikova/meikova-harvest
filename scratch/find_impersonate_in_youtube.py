import os

ytdlp_dir = "D:\\JOB\\DEV\\EveryThingDownloader\\venv\\Lib\\site-packages\\yt_dlp"
youtube_dir = os.path.join(ytdlp_dir, "extractor", "youtube")

for root, dirs, files in os.walk(youtube_dir):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                if "impersonate" in content.lower():
                    lines = content.splitlines()
                    for idx, line in enumerate(lines):
                        if "impersonate" in line.lower():
                            rel_path = os.path.relpath(path, ytdlp_dir)
                            print(f"{rel_path}:{idx+1}: {line.strip()}")
            except Exception as e:
                pass
