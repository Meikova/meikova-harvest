import os

pkg_path = "D:\\JOB\\DEV\\EveryThingDownloader\\venv\\Lib\\site-packages\\yt_dlp\\extractor\\youtube\\_video.py"
with open(pkg_path, "r", encoding="utf-8") as f:
    lines = f.readlines()
for idx in range(1850 - 1, min(len(lines), 1870)):
    line_safe = lines[idx].encode("ascii", "ignore").decode("ascii")
    print(f"{idx+1}: {line_safe}", end="")
