import os

pkg_path = "D:\\JOB\\DEV\\EveryThingDownloader\\venv\\Lib\\site-packages\\yt_dlp\\YoutubeDL.py"
with open(pkg_path, "r", encoding="utf-8") as f:
    lines = f.readlines()
for idx in range(4320, 4370):
    if idx < len(lines):
        print(f"{idx+1}: {lines[idx]}", end="")
