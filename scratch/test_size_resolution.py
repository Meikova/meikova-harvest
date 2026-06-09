import os
import sys
import json
import traceback
import urllib.request

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import get_url_content_length, parse_threads_page, extract_instagram_via_gallery_dl

def safe_str(s):
    if s is None:
        return "None"
    if not isinstance(s, str):
        s = str(s)
    return s.encode('ascii', errors='backslashreplace').decode('ascii')

def print_clean_option(res):
    print(f"Title: {safe_str(res.get('title'))}")
    print(f"Duration: {safe_str(res.get('duration'))}")
    print("\nVideo Options (with resolved sizes):")
    for opt in res.get("video_options", []):
        url_snippet = safe_str(opt.get('url', ''))[:60] + "..."
        print(f"  - [{safe_str(opt.get('type'))}] {safe_str(opt.get('label'))}: Size = {safe_str(opt.get('size'))} | URL: {url_snippet}")
    print("\nAudio Options (with estimated sizes):")
    for opt in res.get("audio_options", []):
        print(f"  - {safe_str(opt.get('label'))}: Size = {safe_str(opt.get('size'))}")

def test_threads():
    url = "https://www.threads.net/@chipmunk.8255885/post/DZWqikzmsye"
    print(f"\n--- Testing Threads Extractor with URL: {url} ---")
    try:
        res = parse_threads_page(url, client_id="client_537ngrlf0hnuty574auzds")
        if res.get("status") == "success":
            print("Successfully extracted Threads post metadata!")
            print_clean_option(res)
        else:
            print("Threads extraction failed:", safe_str(res.get("message")))
    except Exception as e:
        print("Error during Threads extraction test:")
        traceback.print_exc()

def test_instagram():
    url = "https://www.instagram.com/p/DYzYggjk8Ms/"
    print(f"\n--- Testing Instagram Extractor with URL: {url} ---")
    try:
        res = extract_instagram_via_gallery_dl(url, client_id="client_537ngrlf0hnuty574auzds")
        if res:
            print("Successfully extracted Instagram post metadata!")
            print_clean_option(res)
        else:
            print("Instagram extraction returned None")
    except Exception as e:
        print("Error during Instagram extraction test:")
        traceback.print_exc()

def test_youtube_subtitles():
    url = "http://127.0.0.1:5000/api/info"
    payload = {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    print("\n--- Testing YouTube Subtitles Size ---")
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode("utf-8"), 
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            if data.get("status") == "success":
                print("Successfully extracted YouTube metadata!")
                print("Subtitles Options (with resolved sizes):")
                for sub in data.get("subtitles", []):
                    print(f"  - {safe_str(sub.get('name'))} ({safe_str(sub.get('lang_code'))}): Size = {safe_str(sub.get('size'))}")
            else:
                print("YouTube extraction failed:", safe_str(data.get("message")))
    except Exception as e:
        print("Error during YouTube subtitles size test:")
        traceback.print_exc()

if __name__ == "__main__":
    test_threads()
    test_instagram()
    test_youtube_subtitles()
