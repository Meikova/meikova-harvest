import requests
import re
import json

url = "https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
resp = requests.get(url, headers=headers, verify=False)
html = resp.text
clean_html = html.replace('\\/', '/').replace('\\', '')

with open("scratch/slug_association_output.txt", "w", encoding="utf-8") as f:
    for idx, match in enumerate(re.finditer(r'"movieSlug"', clean_html)):
        start = max(0, match.start() - 1000)
        end = min(len(clean_html), match.end() + 1000)
        context = clean_html[start:end]
        f.write(f"\n--- Context {idx+1} (Pos: {match.start()}) ---\n")
        f.write(context + "\n")

print("Written to scratch/slug_association_output.txt")
