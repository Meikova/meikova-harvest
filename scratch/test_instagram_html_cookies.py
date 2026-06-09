import yt_dlp
import requests
import re
import os

def test_instagram_html_cookies():
    url = "https://www.instagram.com/p/DY4UckRBiTU/"
    print(f"Fetching HTML with cookies for: {url}")
    
    ydl_opts = {
        "quiet": True,
        "nocheckcertificate": True,
        "cookiesfrombrowser": ("chrome",),
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            cookie_jar = ydl.cookiejar
            cookies_dict = {}
            for cookie in cookie_jar:
                if "instagram.com" in cookie.domain:
                    cookies_dict[cookie.name] = cookie.value
                    
            print(f"Loaded {len(cookies_dict)} cookies.")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://www.instagram.com/"
            }
            
            response = requests.get(url, headers=headers, cookies=cookies_dict, timeout=15)
            print("Status Code:", response.status_code)
            html = response.text
            
            # Save HTML for inspection
            with open("scratch/instagram_post_with_cookies.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("HTML saved to scratch/instagram_post_with_cookies.html")
            
            # Look for og:image
            og_images = re.findall(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html)
            print(f"Found og:image tags: {len(og_images)}")
            for img in og_images:
                print(f"  - {img[:100]}...")
                
            # Look for JSON-LD
            json_ld = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
            print(f"Found JSON-LD blocks: {len(json_ld)}")
            for idx, block in enumerate(json_ld):
                print(f"Block {idx+1} length: {len(block)}")
                
    except Exception as e:
        print("Failed:", e)

if __name__ == "__main__":
    test_instagram_html_cookies()
