import requests
import re

url = "https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256/tap-1"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
resp = requests.get(url, headers=headers, verify=False, timeout=15)
html = resp.text

# Clean up backslashes
clean_html = html.replace('\\/', '/').replace('\\', '')

# Search for the script tags containing player data
script_tags = re.findall(r'<script.*?>.*?</script>', clean_html, re.DOTALL | re.IGNORECASE)
for idx, tag in enumerate(script_tags):
    if '/player/master/' in tag:
        print(f"Found /player/master/ in Script {idx+1} (length {len(tag)}):")
        # Save this script content to a file for easy viewing
        with open("scratch/player_script.js", "w", encoding="utf-8") as f:
            f.write(tag)
        print("Saved script to scratch/player_script.js")
        
        # Let's search for domains in this script
        domains = re.findall(r'https?://[a-zA-Z0-9.-]+', tag)
        print(f"Unique domains in this script: {set(domains)}")
        break
