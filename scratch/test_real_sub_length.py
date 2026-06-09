import yt_dlp
import requests

def test():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        # Test manual subtitle
        en_url = info.get("subtitles", {}).get("en", [{}])[0].get("url")
        print("Manual EN Sub URL:", en_url)
        if en_url:
            r_head = requests.head(en_url, timeout=5)
            print("  HEAD Status:", r_head.status_code)
            print("  HEAD Headers Content-Length:", r_head.headers.get("content-length"))
            print("  HEAD Headers Transfer-Encoding:", r_head.headers.get("transfer-encoding"))
            
            r_get = requests.get(en_url, timeout=5)
            print("  GET Status:", r_get.status_code)
            print("  GET Headers Content-Length:", r_get.headers.get("content-length"))
            print("  GET text size:", len(r_get.text))
            
        # Test auto subtitle
        vi_url = info.get("automatic_captions", {}).get("vi", [{}])[0].get("url")
        print("\nAuto VI Sub URL:", vi_url)
        if vi_url:
            r_head = requests.head(vi_url, timeout=5)
            print("  HEAD Status:", r_head.status_code)
            print("  HEAD Headers Content-Length:", r_head.headers.get("content-length"))
            print("  HEAD Headers Transfer-Encoding:", r_head.headers.get("transfer-encoding"))
            
            r_get = requests.get(vi_url, timeout=5)
            print("  GET Status:", r_get.status_code)
            print("  GET Headers Content-Length:", r_get.headers.get("content-length"))
            print("  GET text size:", len(r_get.text))

if __name__ == "__main__":
    test()
