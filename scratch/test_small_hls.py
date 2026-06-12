import yt_dlp
import os
import static_ffmpeg

static_ffmpeg.add_paths()

url = "https://vip.opstream90.com/20260605/33879_0038c2d2/index.m3u8"
temp_dir = os.path.abspath("scratch/test_temp_small")
os.makedirs(temp_dir, exist_ok=True)

# Remove any old file
for f in os.listdir(temp_dir):
    try: os.remove(os.path.join(temp_dir, f))
    except: pass

ydl_opts = {
    "outtmpl": os.path.join(temp_dir, "media.%(ext)s"),
    "nocheckcertificate": True,
    "verbose": True,
    "quiet": False,
    "no_warnings": False,
    "noplaylist": True,
    "format": "best",
    "merge_output_format": "mp4",
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    print("Starting download...")
    ydl.download([url])
    print("Finished download call.")
