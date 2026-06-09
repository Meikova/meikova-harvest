import requests

def test():
    # Let's use the actual URL structure for manual subtitles from timedtext API
    url = "https://www.youtube.com/api/timedtext?v=dQw4w9WgXcQ&lang=en&fmt=vtt"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    print("Testing HEAD request...")
    try:
        r_head = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
        print("HEAD Status:", r_head.status_code)
        print("HEAD Content-Length:", r_head.headers.get("content-length"))
        print("HEAD Content-Type:", r_head.headers.get("content-type"))
    except Exception as e:
        print("HEAD failed:", e)

    print("\nTesting GET request...")
    try:
        r_get = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
        print("GET Status:", r_get.status_code)
        print("GET Content-Length:", r_get.headers.get("content-length"))
        print("GET Content-Type:", r_get.headers.get("content-type"))
        print("GET Content snippet:", r_get.text[:200])
    except Exception as e:
        print("GET failed:", e)

if __name__ == "__main__":
    test()
