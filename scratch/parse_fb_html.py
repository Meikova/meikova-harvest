import re
import json
import urllib.parse

with open("scratch/fb_externalhit.html", "r", encoding="utf-8") as f:
    html = f.read()

print(f"Total length: {len(html)}")

# Find all JSON scripts
scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
print(f"Found {len(scripts)} application/json script tags.")

# Find all links containing fbcdn.net/v/
# Let's search for image urls
img_urls = set()
for url in re.findall(r'https://[^\s"\'>]+?\.fbcdn\.net/[^\s"\'>]+', html):
    # Unescape characters
    url_clean = url.replace("\\/", "/").replace("\\u0025", "%").replace("&amp;", "&")
    url_clean = urllib.parse.unquote(url_clean)
    img_urls.add(url_clean)

print(f"\nFound {len(img_urls)} raw fbcdn URLs.")

# Let's inspect some of them
jpg_urls = [u for u in img_urls if ".jpg" in u.lower()]
print(f"Found {len(jpg_urls)} JPG URLs.")
for idx, u in enumerate(sorted(jpg_urls)[:15]):
    # Trim parameters to make it easier to read
    base = u.split("?")[0]
    print(f"[{idx+1}] {base} | full length: {len(u)}")
