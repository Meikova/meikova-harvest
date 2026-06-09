import os
import subprocess
import static_ffmpeg
static_ffmpeg.add_paths()

# Find the downloaded video file
temp_dirs = [d for d in os.listdir("downloads") if d.startswith("temp_")]
if not temp_dirs:
    print("No downloaded temp folders found.")
    sys.exit(1)

# Sort by modification time to find the latest
temp_dirs.sort(key=lambda x: os.path.getmtime(os.path.join("downloads", x)), reverse=True)
video_file = os.path.join("downloads", temp_dirs[0], "media.mp4")

print(f"Latest downloaded video: {video_file}")

# Extract frame at 2 seconds
output_2s = "scratch/frame_2s.jpg"
command_2s = [
    "ffmpeg", "-y",
    "-ss", "00:00:02",
    "-i", video_file,
    "-vframes", "1",
    "-q:v", "2",
    output_2s
]

# Extract frame at 5 seconds
output_5s = "scratch/frame_5s.jpg"
command_5s = [
    "ffmpeg", "-y",
    "-ss", "00:00:05",
    "-i", video_file,
    "-vframes", "1",
    "-q:v", "2",
    output_5s
]

try:
    subprocess.run(command_2s, capture_output=True)
    subprocess.run(command_5s, capture_output=True)
    print("Frames extracted successfully!")
    if os.path.exists(output_2s):
        print(f"2s Frame Size: {os.path.getsize(output_2s)} bytes")
    if os.path.exists(output_5s):
        print(f"5s Frame Size: {os.path.getsize(output_5s)} bytes")
except Exception as e:
    print("Extraction failed:", e)
