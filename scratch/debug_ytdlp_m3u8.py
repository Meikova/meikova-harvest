import yt_dlp
import os
import static_ffmpeg

static_ffmpeg.add_paths()

url = "https://vip.opstream90.com/20260605/33879_0038c2d2/index.m3u8"
temp_dir = os.path.abspath("scratch/test_temp")
os.makedirs(temp_dir, exist_ok=True)

try:
    from yt_dlp.networking.impersonate import ImpersonateTarget
    ydl_opts = {
        "outtmpl": os.path.join(temp_dir, "media.%(ext)s"),
        "nocheckcertificate": True,
        "verbose": True,
        "quiet": False,
        "no_warnings": False,
        "noplaylist": True,
        "format": "best",
        "merge_output_format": "mp4",
        "impersonate": ImpersonateTarget.from_str("chrome"),
        "cookiesfrombrowser": "auto",
    }
except Exception:
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
    ydl.download([url])
