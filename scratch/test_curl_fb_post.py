import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import TEMP_DOWNLOAD_DIR

url = "https://www.facebook.com/share/p/1B9Tkjw1tE/"
client_id = "client_lvnnn0l2zy8d6g9idw3j9a"

cookie_file = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")

command = [
    "curl", "-s", "-L",
    "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "-H", "Accept-Language: vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
]
if os.path.exists(cookie_file):
    command.extend(["-b", cookie_file])
command.append(url)

import subprocess
res = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
html = res.stdout

# Save to file
out_path = "scratch/fb_post_html.html"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Dumped HTML length: {len(html)}")
# Look for Trương Vũ or Rise of Kingdom
print("Contains 'Trương Vũ':", "Trương Vũ" in html or "Truong Vu" in html)
print("Contains 'riseofkingdom':", "riseofkingdom" in html or "Rise of Kingdom" in html or "rise of kingdom" in html)
print("Contains 'FUTA':", "FUTA" in html or "futa" in html)
