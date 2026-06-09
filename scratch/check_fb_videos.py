import re
import urllib.parse

with open("scratch/fb_externalhit.html", "r", encoding="utf-8") as f:
    html = f.read()

# Let's search for mp4 or playable_url
mp4_urls = set()
for url in re.findall(r'https://[^\s"\'>]+?\.fbcdn\.net/[^\s"\'>]+', html):
    url_clean = url.replace("\\/", "/").replace("\\u0025", "%").replace("&amp;", "&")
    url_clean = urllib.parse.unquote(url_clean)
    if ".mp4" in url_clean.lower() or "playable" in url_clean.lower() or "video" in url_clean.lower():
        mp4_urls.add(url_clean)

print(f"Found {len(mp4_urls)} video-related fbcdn URLs:")
for idx, u in enumerate(sorted(mp4_urls)):
    print(f"[{idx+1}] {u.split('?')[0]}")
