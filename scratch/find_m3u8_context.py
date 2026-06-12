import requests
import re
import urllib3
import sys
urllib3.disable_warnings()

url = "https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256/tap-1"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    resp = requests.get(url, headers=headers, verify=False, timeout=15)
    html = resp.text
    
    clean_html = html.replace('\\/', '/').replace('\\', '')
    
    matches = list(re.finditer(r'https?://[^\s"\']+\.m3u8[^\s"\']*', clean_html))
    
    output = []
    output.append(f"Found {len(matches)} m3u8 links in cleaned HTML:")
    
    for idx, m in enumerate(matches):
        start = max(0, m.start() - 200)
        end = min(len(clean_html), m.end() + 200)
        context = clean_html[start:end].replace('\n', ' ').strip()
        output.append(f"\n[{idx}] Link: {m.group(0)}")
        output.append(f"Context: ... {context} ...")
        
    with open("scratch/m3u8_contexts.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    print("Done! Output saved to scratch/m3u8_contexts.txt")
except Exception as e:
    print(f"Error: {e}")
