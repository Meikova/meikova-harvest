import requests
import os

url = "https://www.facebook.com/share/p/18KCdDUac7/"
cookies_path = "downloads/cookies/cookies_client_537ngrlf0hnuty574auzds.txt"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
})

# Load Netscape cookies
if os.path.exists(cookies_path):
    print("Loading cookies...")
    with open(cookies_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 7:
                domain = parts[0]
                name = parts[5]
                value = parts[6]
                if "facebook" in domain:
                    session.cookies.set(name, value, domain=domain)

print(f"Active cookies for session: {session.cookies.get_dict()}")

print("Fetching URL...")
r = session.get(url, timeout=10)
print(f"Status: {r.status_code}")
print(f"Final URL: {r.url}")
print(f"HTML length: {len(r.text)}")

with open("scratch/fb_with_cookies.html", "w", encoding="utf-8") as f:
    f.write(r.text)
