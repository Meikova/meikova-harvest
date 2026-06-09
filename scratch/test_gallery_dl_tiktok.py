import subprocess
import json
import os
import sys

url = "https://www.tiktok.com/@mi3k_18dp/video/7649036378268781842"
cookie_file = "downloads/cookies/cookies_client_537ngrlf0hnuty574auzds.txt"

# gallery-dl arguments
# -j is for json output
python_exe = sys.executable
cmd = [python_exe, "-m", "gallery_dl", "-j", url]

if os.path.exists(cookie_file):
    cmd.extend(["--cookies", cookie_file])

print("Running command:", " ".join(cmd))
try:
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    print("Return Code:", res.returncode)
    print("Output lines count:", len(res.stdout.splitlines()))
    print("Output preview (first 1000 chars):")
    print(res.stdout[:1000])
    print("Error output:")
    print(res.stderr)
except Exception as e:
    print("Failed to run gallery-dl:", e)
