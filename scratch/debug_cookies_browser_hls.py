import sys
import os
import static_ffmpeg
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
static_ffmpeg.add_paths()

sys.path.append(os.path.abspath('.'))
from utils.ytdl import create_ydl_instance

url = "https://vip.opstream90.com/20260605/33879_0038c2d2/index.m3u8"
temp_dir = os.path.abspath("scratch/test_temp_cookies")
os.makedirs(temp_dir, exist_ok=True)

ydl_opts = {
    "outtmpl": os.path.join(temp_dir, "media.%(ext)s"),
    "nocheckcertificate": True,
    "verbose": True,
    "quiet": False,
    "no_warnings": False,
    "noplaylist": True,
    "format": "best",
    "merge_output_format": "mp4",
    "cookiesfrombrowser": "auto",
}

try:
    with create_ydl_instance(ydl_opts, url, "test_client") as ydl:
        ydl.download([url])
except Exception as e:
    print(f"\nCaught Exception during download: {e}")
