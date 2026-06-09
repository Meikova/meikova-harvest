import sys
import os
sys.path.append(os.path.abspath('.'))

import yt_dlp
import subprocess
import time
import static_ffmpeg
static_ffmpeg.add_paths()

url = "https://www.facebook.com/FuzeTeaVN/videos/1305800194990596/?rdid=MPAnduUW537wyGJ4#"

print("Extracting formats using yt-dlp...")
ydl_opts = {
    'ignoreerrors': True,
    'no_color': True,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    
if not info:
    print("Failed to get info")
    sys.exit(1)

# Find the lowest resolution video format URL
video_formats = [f for f in info.get("formats", []) if f.get("vcodec") != "none" and f.get("url")]
if not video_formats:
    print("No video formats found")
    sys.exit(1)

# Sort by height to find the lowest resolution
video_formats.sort(key=lambda x: x.get("height") or 0)
target_format = video_formats[0]
stream_url = target_format.get("url")

print(f"Target format: {target_format.get('resolution')}p | URL: {stream_url[:80]}...")

# Run ffmpeg to extract the first frame
print("Extracting first frame using ffmpeg...")
start_time = time.time()
output_jpg = "scratch/ffmpeg_extracted_thumbnail.jpg"

# Command to extract frame at 3s quickly
output_3s = "scratch/ffmpeg_extracted_3s.jpg"
command_3s = [
    "ffmpeg",
    "-y",
    "-ss", "00:00:03",
    "-i", stream_url,
    "-vframes", "1",
    "-q:v", "2",
    output_3s
]

# Command to extract frame at 5s quickly
output_5s = "scratch/ffmpeg_extracted_5s.jpg"
command_5s = [
    "ffmpeg",
    "-y",
    "-ss", "00:00:05",
    "-i", stream_url,
    "-vframes", "1",
    "-q:v", "2",
    output_5s
]

try:
    print("Extracting frame at 3s...")
    res = subprocess.run(command_3s, capture_output=True, text=True, timeout=10)
    print("3s Return code:", res.returncode)
    
    print("Extracting frame at 5s...")
    res = subprocess.run(command_5s, capture_output=True, text=True, timeout=10)
    print("5s Return code:", res.returncode)
    
    duration = time.time() - start_time
    print(f"FFmpeg duration: {duration:.2f} seconds")
    
    if os.path.exists(output_3s):
        print(f"Successfully extracted 3s frame! Size: {os.path.getsize(output_3s)} bytes")
    if os.path.exists(output_5s):
        print(f"Successfully extracted 5s frame! Size: {os.path.getsize(output_5s)} bytes")
except Exception as e:
    print("FFmpeg failed:", e)
