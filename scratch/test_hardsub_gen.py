import os
import subprocess
import static_ffmpeg

static_ffmpeg.add_paths()

os.makedirs("scratch", exist_ok=True)
video_path = "scratch/dummy.mp4"
vtt_path = "scratch/dummy.vtt"
output_path = "scratch/dummy_hardsubbed.mp4"

# 1. Create a dummy 3-second video
print("Creating dummy video...")
cmd_video = [
    "ffmpeg", "-y",
    "-f", "lavfi", "-i", "testsrc=duration=3:size=640x360:rate=30",
    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
    "-t", "3",
    "-c:v", "libx264", "-c:a", "aac",
    video_path
]
subprocess.run(cmd_video, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 2. Create a dummy VTT file
print("Creating dummy VTT...")
vtt_content = """WEBVTT

00:00:01.000 --> 00:00:02.500
Xin chào thế giới!
"""
with open(vtt_path, "w", encoding="utf-8") as f:
    f.write(vtt_content)

# 3. Test relative path subtitles filter
# We convert the absolute path to a relative path from the current working directory!
abs_vtt = os.path.abspath(vtt_path)
rel_vtt = os.path.relpath(abs_vtt)
# Replace backslashes with forward slashes
rel_vtt = rel_vtt.replace('\\', '/')
# Escape single quotes and colons
rel_vtt = rel_vtt.replace("'", "'\\\\''")
rel_vtt = rel_vtt.replace(":", "\\\\:")
sub_filter = f"subtitles='{rel_vtt}'"
print(f"Subtitles filter path: {sub_filter}")

cmd_hardsub = [
    "ffmpeg", "-y",
    "-i", video_path,
    "-vf", sub_filter,
    "-c:v", "libx264", "-preset", "superfast", "-crf", "23",
    "-c:a", "copy",
    output_path
]

print("Running FFmpeg hardsubbing...")
res = subprocess.run(cmd_hardsub, capture_output=True, text=True)
if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
    print("SUCCESS! Output size:", os.path.getsize(output_path))
else:
    print("FAILED!")
    print(res.stderr)
