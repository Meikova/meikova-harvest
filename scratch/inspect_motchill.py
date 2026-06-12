import requests
import re
import urllib3
urllib3.disable_warnings()

url = "https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256/tap-1"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,vi;q=0.8"
}

try:
    resp = requests.get(url, headers=headers, verify=False, timeout=15)
    print(f"Status Code: {resp.status_code}")
    html = resp.text
    print(f"HTML Length: {len(html)} characters")
    
    # Let's search for script tags, iframes, or m3u8/mp4 URLs
    iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    print(f"\nFound {len(iframes)} iframes:")
    for iframe in iframes:
        print(f" - {iframe}")
        
    m3u8_links = re.findall(r'https?://[^\s"\']+\.m3u8[^\s"\']*', html)
    print(f"\nFound {len(m3u8_links)} direct m3u8 links:")
    for link in m3u8_links:
        print(f" - {link}")
        
    mp4_links = re.findall(r'https?://[^\s"\']+\.mp4[^\s"\']*', html)
    print(f"\nFound {len(mp4_links)} direct mp4 links:")
    for link in mp4_links:
        print(f" - {link}")
        
    # Search for common video player config names (e.g. player, video, source, iframe, embed)
    print("\nSearching for video-related patterns in script tags:")
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    for i, s in enumerate(scripts):
        if any(keyword in s.lower() for keyword in ["player", "embed", "iframe", "m3u8", "video", "source", "link", "url"]):
            print(f"Script #{i} matches keywords (len={len(s)}). Snippet:")
            lines = [line.strip() for line in s.splitlines() if line.strip()]
            for line in lines[:10]:
                print(f"  {line[:120]}")
            if len(lines) > 10:
                print("  ...")
except Exception as e:
    print(f"Error fetching page: {e}")
