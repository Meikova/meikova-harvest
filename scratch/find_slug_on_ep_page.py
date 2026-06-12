import requests
import re

url = "https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256/tap-1"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
resp = requests.get(url, headers=headers, verify=False)
html = resp.text
clean_html = html.replace('\\/', '/').replace('\\', '')

with open("scratch/ep_page_slug_matches.txt", "w", encoding="utf-8") as f:
    for idx, match in enumerate(re.finditer(r'bai-hoc-dang-doi-1780648256', clean_html)):
        start = max(0, match.start() - 200)
        end = min(len(clean_html), match.end() + 200)
        f.write(f"\n--- Match {idx+1} (Pos: {match.start()}) ---\n")
        f.write(clean_html[start:end] + "\n")

print("Written to scratch/ep_page_slug_matches.txt")
