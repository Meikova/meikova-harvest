import requests
import re

url = "https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
resp = requests.get(url, headers=headers, verify=False)
html = resp.text

# Find occurrences of "bai-hoc-dang-doi-1780648256" in html
with open("scratch/slug_context.txt", "w", encoding="utf-8") as f:
    for idx, match in enumerate(re.finditer(r'bai-hoc-dang-doi-1780648256', html, re.IGNORECASE)):
        start = max(0, match.start() - 250)
        end = min(len(html), match.end() + 250)
        f.write(f"\n--- Match {idx+1} (Pos: {match.start()}) ---\n")
        f.write(html[start:end] + "\n")

print("Written contexts to scratch/slug_context.txt")
