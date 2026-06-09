import requests
import sys

# Set stdout/stderr to UTF-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

url = "https://www.threads.net/t/C6a0S9-I3g6"
headers = {
    "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_patched.html)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

try:
    response = requests.get(url, headers=headers, timeout=15)
    print("Status:", response.status_code)
    print("HTML length:", len(response.text))
    
    with open("scratch/threads_facebookexternalhit.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("Saved to scratch/threads_facebookexternalhit.html")
except Exception as e:
    print("Error:", e)
