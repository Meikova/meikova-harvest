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
    
    # Match escaped/unescaped URLs ending with jpg/png/jpeg
    # Slashes can be / or \/
    pattern = r'https?:?(?:\\/|/)+[^\s"\'>]+?\.(?:jpg|png|jpeg)(?:\?[^\s"\'>]+?)?'
    img_urls = re.findall(pattern, html, re.IGNORECASE)
    
    unique_urls = []
    for u in img_urls:
        clean = u.replace(r'\/', '/').replace(r'\\/', '/').replace('&amp;', '&').strip()
        if clean not in unique_urls:
            unique_urls.append(clean)
            
    print(f"Found {len(unique_urls)} unique image URLs.")
    
    with open("scratch/all_images.txt", "w", encoding="utf-8") as f:
        for u in unique_urls:
            f.write(u + "\n")
    print("Saved to scratch/all_images.txt")

except Exception as e:
    print("Failed to inspect HTML:", e)
