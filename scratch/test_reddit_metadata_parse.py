import sys
import os
sys.path.append(os.getcwd())

import json
import subprocess
from app import extract_reddit_via_gallery_dl, scrape_reddit_fallback

url = "https://www.reddit.com/r/ArtificialInteligence/comments/1u1dkg0/why_is_fable_5_included_only_till_june_22_does/?share_id=W2Gf9TmhJAMw0UJHaj9DE&utm_content=share_button&utm_medium=web3x&utm_name=web3xcss&utm_source=share&utm_term=1"

print("--- Testing extract_reddit_via_gallery_dl ---")
try:
    info = extract_reddit_via_gallery_dl(url, "test_client")
    print("Success! Keys in info:", info.keys())
    print("Platform:", info.get("platform"))
    print("Video options:")
    for opt in info.get("video_options", []):
        print(f"  Format ID: {opt.get('format_id')}, Label: {opt.get('label')}, URL: {opt.get('url')[:100]}...")
except Exception as e:
    print("Failed extract_reddit_via_gallery_dl:", e)

print("\n--- Testing scrape_reddit_fallback ---")
try:
    info_fallback = scrape_reddit_fallback(url, "test_client")
    if info_fallback:
        print("Success! Keys in info_fallback:", info_fallback.keys())
        print("Video options in fallback:")
        for opt in info_fallback.get("video_options", []):
            print(f"  Format ID: {opt.get('format_id')}, Label: {opt.get('label')}, URL: {opt.get('url')[:100]}...")
    else:
        print("Fallback returned None")
except Exception as e:
    print("Failed scrape_reddit_fallback:", e)
