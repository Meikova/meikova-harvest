import sys
import os
sys.path.append(os.getcwd())

import json
import subprocess
from app import extract_reddit_via_gallery_dl, scrape_reddit_fallback

url = "https://www.reddit.com/r/VietnamMemeWar/comments/1u14fnd/giờ_mới_biết_tại_sao_nó_rớt_phỏng_vấn_rồi/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button"

print("--- Testing first URL with extract_reddit_via_gallery_dl ---")
try:
    info = extract_reddit_via_gallery_dl(url, "test_client")
    print("Success! Keys in info:", info.keys())
    print("Platform:", info.get("platform"))
except Exception as e:
    print("Failed extract_reddit_via_gallery_dl:", e)

print("\n--- Testing first URL with scrape_reddit_fallback ---")
try:
    info_fallback = scrape_reddit_fallback(url, "test_client")
    if info_fallback:
        print("Success! Keys in info_fallback:", info_fallback.keys())
    else:
        print("Fallback returned None")
except Exception as e:
    print("Failed scrape_reddit_fallback:", e)
