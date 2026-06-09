import requests

url = "https://www.facebook.com/share/p/18KCdDUac7/"
headers = {
    "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_patched.html)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

print("Fetching with facebookexternalhit User-Agent...")
r = requests.get(url, headers=headers, timeout=10)
print(f"Status: {r.status_code}")
print(f"Final URL: {r.url}")
print(f"HTML length: {len(r.text)}")

# Save HTML
with open("scratch/fb_externalhit.html", "w", encoding="utf-8") as f:
    f.write(r.text)

print("Saved HTML to scratch/fb_externalhit.html")
