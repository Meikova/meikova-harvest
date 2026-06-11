import os
import subprocess
import static_ffmpeg

static_ffmpeg.add_paths()

video_path = r"D:\JOB\DEV\EveryThingDownloader\downloads\temp_8b0decc4-ce68-4c9e-90ba-facef59f9449\media.mp4"
vtt_path = r"D:\JOB\DEV\EveryThingDownloader\downloads\temp_8b0decc4-ce68-4c9e-90ba-facef59f9449\media.vi.vtt"
output_path = r"D:\JOB\DEV\EveryThingDownloader\downloads\temp_8b0decc4-ce68-4c9e-90ba-facef59f9449\media_hardsubbed.mp4"

def format_subtitles_filter_path(path):
    path = path.replace('\\', '/')
    if len(path) > 1 and path[1] == ':':
        # Escape the colon for Windows drive letter in FFmpeg filters
        path = path[0] + '\\\\:' + path[2:]
    # Escape single quotes
    path = path.replace("'", "'\\\\''")
    return f"subtitles='{path}'"

sub_filter = format_subtitles_filter_path(vtt_path)
print(f"Subtitles filter path: {sub_filter}")

cmd = [
    "ffmpeg", "-y",
    "-i", video_path,
    "-vf", sub_filter,
    "-c:v", "libx264", "-preset", "superfast", "-crf", "23",
    "-c:a", "copy",
    output_path
]

print("Running FFmpeg hardsubbing...")
res = subprocess.run(cmd, capture_output=True, text=True)
if res.returncode == 0:
    print("SUCCESS! Output size:", os.path.getsize(output_path))
else:
    print("FAILED!")
    print(res.stderr)
