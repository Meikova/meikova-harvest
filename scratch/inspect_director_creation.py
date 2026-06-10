import inspect
import yt_dlp

# Let's inspect where _request_director is created in YoutubeDL
import os
pkg_path = "D:\\JOB\\DEV\\EveryThingDownloader\\venv\\Lib\\site-packages\\yt_dlp\\YoutubeDL.py"
with open(pkg_path, "r", encoding="utf-8") as f:
    content = f.read()

# Let's search for _request_director or request_director
lines = content.splitlines()
for idx, line in enumerate(lines):
    if "request_director" in line.lower():
        print(f"{idx+1}: {line}")
