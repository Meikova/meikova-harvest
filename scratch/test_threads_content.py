import requests
import re
import sys

# Set stdout/stderr to UTF-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

url = "https://www.threads.net/@chipmunk.8255885/post/DZWqikzmsye"
headers = {
    "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_patched.html)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

print("Fetching page with facebookexternalhit User-Agent...")
res = requests.get(url, headers=headers, timeout=15)
print("Status Code:", res.status_code)
html = res.text

print("Html length:", len(html))

# Let's search for 'scontent' or 'cdninstagram' in html
cdns = re.findall(r'https?://[^\s"\'\\>]+(?:scontent|cdninstagram)[^\s"\'\\>]+', html)
print(f"Found {len(cdns)} CDN links.")
for idx, cdn in enumerate(cdns[:10]):
    print(f"  {idx+1}: {cdn[:120]}")
