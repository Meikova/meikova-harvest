import os
import time

TEMP_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "downloads")
cookie_file = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", "cookies_client_lvnnn0l2zy8d6g9idw3j9a.txt")

if not os.path.exists(cookie_file):
    print("Cookie file does not exist!")
    exit(1)

print("Cookie File size:", os.path.getsize(cookie_file))
print("Last modified:", time.ctime(os.path.getmtime(cookie_file)))

fb_cookies = []
with open(cookie_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            domain = parts[0]
            name = parts[5]
            expires = int(parts[4])
            if "facebook" in domain or "fb.com" in domain:
                fb_cookies.append((domain, name, expires))

print(f"\nFacebook cookies count: {len(fb_cookies)}")
for d, n, e in fb_cookies:
    status = "Active" if e > time.time() else "Expired"
    print(f" - Domain: {d}, Name: {n}, Expiration: {time.ctime(e)} ({status})")
