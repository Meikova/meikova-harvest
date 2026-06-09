import os
import sys
import json
import yt_dlp

def test_yt_subs():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print("Manual Subtitles keys:", list(info.get("subtitles", {}).keys()))
        en_subs = info.get("subtitles", {}).get("en", [])
        print("First EN sub structure:")
        if en_subs:
            print(json.dumps(en_subs[0], indent=2))
        else:
            print("No English manual subtitles found.")
            
        print("\nAutomatic Subtitles keys:", list(info.get("automatic_captions", {}).keys())[:10])
        vi_auto = info.get("automatic_captions", {}).get("vi", [])
        print("First VI auto caption structure:")
        if vi_auto:
            print(json.dumps(vi_auto[0], indent=2))

if __name__ == "__main__":
    test_yt_subs()
