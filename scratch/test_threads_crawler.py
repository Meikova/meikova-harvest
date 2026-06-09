import requests
import re
import sys

# Set stdout/stderr to UTF-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

url = "https://www.threads.net/t/C6a0S9-I3g6" # Standard threads post

user_agents = [
    "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_patched.html)",
    "Twitterbot/1.0",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def find_meta_property(html, property_name):
    # Regex to extract property content regardless of order of attributes
    match = re.search(rf'<meta\s+[^>]*property="{property_name}"\s+[^>]*content="([^"]+)"', html)
    if not match:
        match = re.search(rf'<meta\s+[^>]*content="([^"]+)"\s+[^>]*property="{property_name}"', html)
    return match.group(1) if match else "Not found"

for ua in user_agents:
    print(f"\n--- Testing User-Agent: {ua[:50]}... ---")
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print("Status code:", response.status_code)
        
        html = response.text
        
        og_video = find_meta_property(html, "og:video")
        og_image = find_meta_property(html, "og:image")
        og_description = find_meta_property(html, "og:description")
        og_title = find_meta_property(html, "og:title")
        
        print("og:title:", og_title)
        print("og:description:", og_description[:100] + "..." if og_description != "Not found" else "Not found")
        print("og:image:", og_image[:100] + "..." if og_image != "Not found" else "Not found")
        print("og:video:", og_video[:100] + "..." if og_video != "Not found" else "Not found")
        
    except Exception as e:
        print("Error:", e)
