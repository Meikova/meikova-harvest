import requests
import re
import urllib3
urllib3.disable_warnings()

url = "https://phimchillhd.net/phim/giao-duc-chan-chinh/tap-1_1353070.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"
}

try:
    resp = requests.get(url, headers=headers, verify=False, timeout=15)
    print(f"Status Code: {resp.status_code}")
    html = resp.text
    print(f"HTML Length: {len(html)} characters")
    
    with open("scratch/phimchill_ep1.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved HTML to scratch/phimchill_ep1.html")

    # Let's search for some common iframe / player option / script tags
    print("\nLooking for dooplay_player_option:")
    dooplay = re.findall(r'dooplay_player_option', html)
    print(f"dooplay_player_option count: {len(dooplay)}")
    
    print("\nLooking for HalimThemes / Halim player:")
    halim = re.findall(r'halim', html, re.IGNORECASE)
    print(f"halim count: {len(halim)}")
    
    print("\nLooking for player options, servers or iframe elements:")
    iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    print(f"Found {len(iframes)} iframes:")
    for iframe in iframes:
        print(f"  - {iframe}")
        
    print("\nLooking for player_option or similar server choice keywords:")
    # Look for lists or divs with server options
    server_list = re.findall(r'(?:server|episode|play-option|btn-episode)[^>]*>', html, re.IGNORECASE)
    print(f"Found {len(server_list)} elements matching server/episode/play-option/btn-episode. Examples:")
    for s in server_list[:20]:
        print(f"  - {s[:100]}")

except Exception as e:
    print(f"Request failed: {e}")
