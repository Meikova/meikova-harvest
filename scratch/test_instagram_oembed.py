import requests
import json

def test_instagram_oembed():
    url = "https://api.instagram.com/oembed/?url=https://www.instagram.com/p/DY4UckRBiTU/"
    print(f"Querying Instagram oEmbed: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print("Status Code:", response.status_code)
        if response.status_code == 200:
            data = response.json()
            print("Successfully retrieved oEmbed data!")
            print(json.dumps(data, indent=2))
        else:
            print("Response:", response.text)
    except Exception as e:
        print("Failed:", e)

if __name__ == "__main__":
    test_instagram_oembed()
