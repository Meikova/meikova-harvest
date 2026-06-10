import requests
import re
import json

url = "https://www.reddit.com/r/ArtificialInteligence/s/GdwARR3iIt"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print("Trying to resolve URL:")
try:
    res = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
    print("Resolved URL:", res.url)
    print("Status code:", res.status_code)
    # Check if we got old.reddit or www.reddit
    url = res.url
except Exception as e:
    print("Failed to resolve URL:", e)

# Test the backend regex match
import re as re_reddit
is_share_link = re_reddit.match(r"https?://(?:www\.|old\.|new\.)?reddit\.com/r/[^/]+/s/[^/?]+", url)
print("Regex matches share link pattern before resolve?:", bool(re_reddit.match(r"https?://(?:www\.|old\.|new\.)?reddit\.com/r/[^/]+/s/[^/?]+", "https://www.reddit.com/r/ArtificialInteligence/s/GdwARR3iIt")))

# Let's see if we extract it via gallery-dl or old_reddit or yt-dlp.
import subprocess
gallery_dl_path = "d:/JOB/DEV/EveryThingDownloader/venv/Scripts/gallery-dl.exe"
print("\nInvoking gallery-dl with:", res.url)
cmd = [gallery_dl_path, "-j", res.url]
try:
    res_g = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("gallery-dl code:", res_g.returncode)
    print("gallery-dl stdout length:", len(res_g.stdout))
    print("gallery-dl stderr:", res_g.stderr[:500])
except Exception as e:
    print("gallery-dl failed:", e)

import yt_dlp
print("\nInvoking yt-dlp with:", res.url)
try:
    ydl_opts = {'skip_download': True, 'dumpjson': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(res.url, download=False)
        print("yt-dlp title:", info.get("title"))
except Exception as e:
    print("yt-dlp failed:", e)
