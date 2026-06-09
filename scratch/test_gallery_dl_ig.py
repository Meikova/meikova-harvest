import urllib.request
import json
import time

def test_api():
    url = "http://127.0.0.1:5000/api/info"
    # Target Instagram post URL from the user
    target_url = "https://www.instagram.com/p/DYzYggjk8Ms/"
    client_id = "client_537ngrlf0hnuty574auzds" # Reuse the client ID with cookies
    
    data = json.dumps({"url": target_url, "client_id": client_id}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    print("Testing Instagram API extraction via /api/info...")
    try:
        with urllib.request.urlopen(req) as res:
            response_data = json.loads(res.read().decode("utf-8"))
            print("Response Status:", response_data.get("status"))
            
            title = response_data.get("title", "")
            print("Title:", title.encode('utf-8', 'ignore').decode('ascii', 'ignore'))
            
            uploader = response_data.get("uploader", "")
            print("Uploader:", uploader.encode('utf-8', 'ignore').decode('ascii', 'ignore'))
            
            print("Thumbnail:", response_data.get("thumbnail"))
            print("Number of video options:", len(response_data.get("video_options", [])))
            print("Video Options:")
            for opt in response_data.get("video_options", []):
                print(f"  - {opt.get('label')}: {opt.get('url')[:80]}...")
            print("Number of images:", len(response_data.get("images", [])))
            print("Images (first 3):")
            for img in response_data.get("images", [])[:3]:
                print(f"  - {img.get('label')}: {img.get('url')[:80]}...")
            print("Number of audio options:", len(response_data.get("audio_options", [])))
            print("Audio Options:")
            for opt in response_data.get("audio_options", []):
                print(f"  - {opt.get('label')}: {opt.get('url')[:80]}...")
    except Exception as e:
        print("API test failed:", e)

if __name__ == "__main__":
    test_api()
