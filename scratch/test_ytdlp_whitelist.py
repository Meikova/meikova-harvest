import yt_dlp
import os
import static_ffmpeg

static_ffmpeg.add_paths()

url = "https://fcloud.live/player/master/1780659930603_ep135023_episode_135023"
temp_dir = "scratch/test_temp"
os.makedirs(temp_dir, exist_ok=True)

ydl_opts = {
    "outtmpl": os.path.join(temp_dir, "media.%(ext)s"),
    "nocheckcertificate": True,
    "verbose": True,
    "quiet": False,
    "external_downloader_args": {
        "ffmpeg": ["-protocol_whitelist", "file,http,https,tcp,tls,crypto,data"]
    },
    "hls_use_mpegts": True, # force mpegts download
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    try:
        ydl.download([url])
        print("DOWNLOAD SUCCESSFUL!")
    except Exception as e:
        print(f"DOWNLOAD FAILED: {e}")
