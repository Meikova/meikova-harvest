import sys
import os
sys.path.append(os.path.abspath('.'))

import yt_dlp

url = "https://www.facebook.com/FuzeTeaVN/videos/1305800194990596/"
cookies_file = "downloads/cookies/cookies_client_537ngrlf0hnuty574auzds.txt"

print("--- Test 1: WITHOUT cookies ---")
ydl_opts_no_cookies = {
    'ignoreerrors': False,
    'no_color': True,
}
try:
    with yt_dlp.YoutubeDL(ydl_opts_no_cookies) as ydl:
        info = ydl.extract_info(url, download=False)
        print("Success without cookies!")
        print("Title:", info.get("title"))
except Exception as e:
    print("Failed without cookies:", e)

print("\n--- Test 2: WITH cookies ---")
ydl_opts_with_cookies = {
    'ignoreerrors': False,
    'no_color': True,
    'cookiefile': cookies_file
}
try:
    with yt_dlp.YoutubeDL(ydl_opts_with_cookies) as ydl:
        info = ydl.extract_info(url, download=False)
        print("Success with cookies!")
        print("Title:", info.get("title"))
except Exception as e:
    print("Failed with cookies:", e)
