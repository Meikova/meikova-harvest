import sys
import os
sys.path.append(os.path.abspath('.'))

import yt_dlp
import json

url = "https://www.facebook.com/FuzeTeaVN/videos/1305800194990596/?rdid=MPAnduUW537wyGJ4#"

ydl_opts = {
    'ignoreerrors': True,
    'no_color': True,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    if info:
        print("Default Thumbnail:", info.get("thumbnail"))
        print("\nAll Thumbnails:")
        thumbnails = info.get("thumbnails", [])
        for idx, t in enumerate(thumbnails):
            print(f"[{idx}] {t.get('id')} - {t.get('width')}x{t.get('height')}: {t.get('url')}")
    else:
        print("Failed to extract info")
