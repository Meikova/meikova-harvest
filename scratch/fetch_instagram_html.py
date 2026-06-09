import requests
import re
import os

def fetch_instagram_html():
    url = "https://www.instagram.com/p/DY4UckRBiTU/"
    print(f"Fetching HTML for: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print("Status Code:", response.status_code)
        html = response.text
        
        # Save HTML for inspection
        with open("scratch/instagram_post.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("HTML saved to scratch/instagram_post.html")
        
        # Look for og:image
        og_images = re.findall(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html)
        print(f"Found og:image tags: {len(og_images)}")
        for img in og_images:
            print(f"  - {img[:100]}...")
            
        # Look for og:video
        og_videos = re.findall(r'<meta[^>]*property=["\']og:video["\'][^>]*content=["\']([^"\']+)["\']', html)
        print(f"Found og:video tags: {len(og_videos)}")
        for vid in og_videos:
            print(f"  - {vid[:100]}...")
            
        # Look for JSON-LD
        json_ld = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
        print(f"Found JSON-LD blocks: {len(json_ld)}")
        for idx, block in enumerate(json_ld):
            print(f"Block {idx+1} length: {len(block)}")
            
    except Exception as e:
        print("Failed:", e)

if __name__ == "__main__":
    fetch_instagram_html()
