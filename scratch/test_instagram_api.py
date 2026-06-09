import urllib.request
import json
import sys

def test_instagram_api():
    url = "http://127.0.0.1:5000/api/info"
    test_urls = [
        "https://www.instagram.com/p/Cw9p1o_I0W1/",      # Carousel / Post
        "https://www.instagram.com/reel/C321456789/",    # Reel
        "https://www.instagram.com/stories/some_user/"   # Story
    ]
    
    for test_url in test_urls:
        print("\n" + "="*50)
        print(f"Testing URL: {test_url}")
        print("="*50)
        
        data = json.dumps({
            "url": test_url,
            "client_id": "test_client_id"
        }).encode("utf-8")
        
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        
        try:
            with urllib.request.urlopen(req) as res:
                response_data = json.loads(res.read().decode("utf-8"))
                print("Response status code: 200")
                print("Platform Class:", response_data.get("platform_class"))
                print("Platform Label:", response_data.get("platform_label"))
                print("Title:", response_data.get("title"))
                print("Images:", len(response_data.get("images", [])))
                print("Video Options:")
                for opt in response_data.get("video_options", []):
                    print(f"  - {opt.get('label')} ({opt.get('format_id')}) -> {opt.get('url')[:60]}...")
        except urllib.error.HTTPError as e:
            print(f"HTTP Error {e.code}:")
            err_content = e.read().decode("utf-8")
            try:
                err_json = json.loads(err_content)
                print(json.dumps(err_json, indent=2))
            except Exception:
                print(err_content)
        except Exception as e:
            print("Request failed:", e)

if __name__ == "__main__":
    test_instagram_api()
