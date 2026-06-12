import requests
import re

url = "https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, http://x.com/): Gecko/20100101 Firefox/120.0"
}
resp = requests.get(url, headers=headers, verify=False)
html = resp.text

# Let's search for "movie_id" or "id" or "movie" patterns
print("Searching for movie/id patterns:")
matches = re.findall(r'(?i)(movie_id|movieid|id_movie|id|"id"|\bphim\b|postId)\s*[:=]\s*["\']?(\d+)["\']?', html)
for m in matches[:20]:
    print(m)

# Also let's search for the actual movie ID we saw in JSON: "81640"
print("\nSearching for 81640 occurrences context:")
for match in re.finditer(r'81640', html):
    start = max(0, match.start() - 50)
    end = min(len(html), match.end() + 50)
    print(f"Context: ... {html[start:end].strip()} ...")

# Let's search for the other movie ID: "80960"
print("\nSearching for 80960 occurrences context:")
for match in re.finditer(r'80960', html):
    start = max(0, match.start() - 50)
    end = min(len(html), match.end() + 50)
    print(f"Context: ... {html[start:end].strip()} ...")
