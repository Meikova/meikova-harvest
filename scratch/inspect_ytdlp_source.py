import os

pkg_path = "D:\\JOB\\DEV\\EveryThingDownloader\\venv\\Lib\\site-packages\\yt_dlp\\YoutubeDL.py"
if os.path.exists(pkg_path):
    with open(pkg_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    start = max(0, 4210)
    end = min(len(lines), 4250)
    for idx in range(start, end):
        print(f"{idx+1}: {lines[idx]}", end="")
else:
    print("Not found")
