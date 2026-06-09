import yt_dlp
import sys

# Set stdout/stderr to UTF-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

ydl_opts = {
    'quiet': True,
    'no_warnings': True,
}

url = "https://www.threads.net/t/C6a0S9-I3g6" # Standard threads post

print(f"Testing yt-dlp with URL: {url}")
try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print("Success! Info extracted.")
        print("Title:", info.get('title'))
        print("Formats count:", len(info.get('formats', [])))
except Exception as e:
    print("Error:", e)
