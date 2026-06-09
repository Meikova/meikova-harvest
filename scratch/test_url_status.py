import requests
import sys

# Set stdout/stderr to UTF-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

url = "https://www.threads.net/@chipmunk.8255885/post/DZWqikzmsye"
print(f"Requesting: {url}")
res = requests.get(url, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}, allow_redirects=True)
print("Status Code:", res.status_code)
print("Final URL:", res.url)
print("Redirects:", [r.url for r in res.history])
print("Content length:", len(res.text))
