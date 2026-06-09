import requests
import json
import re
import os

url = "https://www.tiktok.com/@mi3k_18dp/video/7649036378268781842"
cookie_file = "downloads/cookies/cookies_client_537ngrlf0hnuty574auzds.txt"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.tiktok.com/"
}

cookies_dict = {}
if os.path.exists(cookie_file):
    try:
        with open(cookie_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) >= 7:
                    cookies_dict[parts[5]] = parts[6]
        print(f"Loaded {len(cookies_dict)} cookies")
    except Exception as e:
        print("Failed to load cookies:", e)

print("Fetching webpage HTML...")
try:
    r = requests.get(url, headers=headers, cookies=cookies_dict, timeout=10)
    print("Status Code:", r.status_code)
    html = r.text
    print("HTML Length:", len(html))
    
    # Search for __UNIVERSAL_DATA_FOR_REHYDRATION__
    match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">([^<]+)</script>', html)
    if match:
        print("Found __UNIVERSAL_DATA_FOR_REHYDRATION__ script!")
        js_text = match.group(1).strip()
        data = json.loads(js_text)
        
        # Save to file for debugging
        with open("scratch/tiktok_rehydration.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print("Saved script contents to scratch/tiktok_rehydration.json")
    else:
        # Search for SIGI_STATE
        sigi_match = re.search(r'<script id="SIGI_STATE" type="application/json">([^<]+)</script>', html)
        if sigi_match:
            print("Found SIGI_STATE script!")
            js_text = sigi_match.group(1).strip()
            data = json.loads(js_text)
            with open("scratch/tiktok_sigi.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("Saved SIGI_STATE to scratch/tiktok_sigi.json")
        else:
            print("Could not find any JSON scripts!")
            
except Exception as e:
    print("Request failed:", e)
