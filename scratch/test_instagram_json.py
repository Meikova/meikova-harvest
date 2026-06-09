import requests
import json
import os

def test_instagram_json():
    shortcode = "DY4UckRBiTU"
    url = f"https://www.instagram.com/p/{shortcode}/?__a=1&__d=dis"
    print(f"Querying Instagram JSON endpoint: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.instagram.com/"
    }
    
    cookies_dict = {}
    # Check if there are cookies files
    cookies_dir = "downloads/cookies"
    if os.path.exists(cookies_dir):
        files = [f for f in os.listdir(cookies_dir) if f.startswith("cookies_")]
        if files:
            cf = os.path.join(cookies_dir, files[0])
            print(f"Loading cookies from: {cf}")
            with open(cf, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        cookies_dict[parts[5]] = parts[6]
                        
    try:
        response = requests.get(url, headers=headers, cookies=cookies_dict, timeout=15)
        print("Status Code:", response.status_code)
        
        # Save response text for debugging
        with open("scratch/instagram_api_resp.json", "w", encoding="utf-8") as f:
            f.write(response.text)
            
        data = response.json()
        print("Successfully parsed JSON response!")
        
        # Check if it has items
        items = data.get("items", [])
        if not items:
            print("No items in response. Graphql wrapper?")
            graphql = data.get("graphql", {})
            media = graphql.get("shortcode_media", {})
        else:
            media = items[0]
            
        if media:
            print("Media found!")
            print("Title/Caption:", media.get("caption", {}).get("text") or media.get("edge_media_to_caption", {}).get("edges", [{}])[0].get("node", {}).get("text"))
            print("Uploader:", media.get("user", {}).get("username") or media.get("owner", {}).get("username"))
            
            # Carousel slides
            carousel_media = media.get("carousel_media") or media.get("edge_sidecar_to_children", {}).get("edges", [])
            print(f"Carousel media entries count: {len(carousel_media)}")
            
    except Exception as e:
        print("Failed to query or parse JSON:", e)
        # Try to print some response content
        try:
            print("Response preview:", response.text[:500])
        except Exception:
            pass

if __name__ == "__main__":
    test_instagram_json()
