import yt_dlp
import requests
import json
import os

def test_instagram_cookies_api():
    url = "https://www.instagram.com/p/DY4UckRBiTU/"
    json_url = f"{url}?__a=1&__d=dis"
    print(f"Testing Instagram API with cookies for: {json_url}")
    
    ydl_opts = {
        "quiet": True,
        "nocheckcertificate": True,
        "cookiesfrombrowser": ("chrome",), # Explicitly chrome
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            cookie_jar = ydl.cookiejar
            print("Successfully retrieved cookie jar from yt-dlp.")
            
            cookies_dict = {}
            for cookie in cookie_jar:
                if "instagram.com" in cookie.domain:
                    cookies_dict[cookie.name] = cookie.value
                    
            print(f"Extracted {len(cookies_dict)} instagram.com cookies.")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://www.instagram.com/",
                "X-IG-App-ID": "936619743392459"
            }
            
            response = requests.get(json_url, headers=headers, cookies=cookies_dict, timeout=15)
            print("Status Code:", response.status_code)
            
            if response.status_code == 200:
                data = response.json()
                print("Parsed JSON successfully!")
                print("Keys:", list(data.keys()))
                
                items = data.get("items", [])
                if items:
                    media = items[0]
                    print("Media Shortcode:", media.get("code"))
                    print("Media Type:", media.get("media_type"))
                    
                    carousel_items = media.get("carousel_media", [])
                    print(f"Carousel entries count: {len(carousel_items)}")
                    
                    # If it's a single image, it doesn't have carousel_media. It has image_versions2
                    if media.get("media_type") == 1:
                        candidates = media.get("image_versions2", {}).get("candidates", [])
                        if candidates:
                            print(f"Single Image URL: {candidates[0].get('url')[:80]}...")
                    
                    for idx, item in enumerate(carousel_items):
                        media_type = item.get("media_type")
                        print(f"Slide {idx+1} Type: {media_type}")
                        if media_type == 1:
                            candidates = item.get("image_versions2", {}).get("candidates", [])
                            if candidates:
                                print(f"  - Photo URL: {candidates[0].get('url')[:80]}...")
                        elif media_type == 2:
                            videos = item.get("video_versions", [])
                            if videos:
                                print(f"  - Video URL: {videos[0].get('url')[:80]}...")
                else:
                    print("No items in JSON response.")
                    print(json.dumps(data, indent=2)[:500])
            else:
                print("Response text:", response.text[:400])
                
    except Exception as e:
        print("Failed:", e)

if __name__ == "__main__":
    test_instagram_cookies_api()
