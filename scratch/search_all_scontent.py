import urllib.request
import re

url = "https://www.facebook.com/FuzeTeaVN/videos/1305800194990596/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8', errors='ignore')
    
    print("Page length:", len(html))
    
    # Broad regex to capture scontent urls
    urls = re.findall(r'https?:?[\\/]*/+[^\s"\'\\<>]+?scontent[^\s"\'\\<>]+', html)
    unique_urls = []
    for u in urls:
        clean = u.replace(r'\/', '/').replace(r'\\/', '/').replace('&amp;', '&').strip()
        clean = clean.split('\\')[0].split('"')[0].split("'")[0]
        if clean not in unique_urls:
            unique_urls.append(clean)
            
    print(f"Found {len(unique_urls)} unique scontent URLs.")
    
    # Filter for jpg, jpeg, png, webp
    image_urls = [u for u in unique_urls if any(ext in u.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp'])]
    print(f"Found {len(image_urls)} unique image FBCDN URLs:")
    for idx, u in enumerate(image_urls):
        print(f"[{idx}] {u[:120]}...")
        
except Exception as e:
    print("Failed to inspect HTML:", e)
