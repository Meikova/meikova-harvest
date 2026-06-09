import requests
import sys
import re

# Set stdout/stderr to UTF-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

session = requests.Session()

page_url = "https://www.threads.net/"
page_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

try:
    print(f"Fetching root page: {page_url}...")
    page_res = session.get(page_url, headers=page_headers, timeout=15)
    print("Page fetch status:", page_res.status_code)
    
    if "Barcelona404ErrorRoot" in page_res.text:
        print("Warning: Page returned 404 Error Component!")
    else:
        print("Page loaded successfully without 404!")

    # Check title
    title_match = re.search(r'<title>(.*?)</title>', page_res.text, re.IGNORECASE)
    print("Page Title:", title_match.group(1) if title_match else "Not found")

except Exception as e:
    print("Error occurred:", e)
