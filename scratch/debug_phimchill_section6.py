import requests
import re
import urllib3
urllib3.disable_warnings()

url = "https://phimchillhd.net/phim/giao-duc-chan-chinh/tap-1_1353070.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://phimchillhd.net/"
}

resp = requests.get(url, headers=headers, verify=False, timeout=10)
page_html = resp.text

episode_pattern = r'\{[^{}]*"server"[^{}]*"name"[^{}]*"slug"[^{}]*"link"[^{}]*\}'
ep_matches = re.findall(episode_pattern, page_html)

print(f"Found {len(ep_matches)} ep matches in page_html.")
for idx, ep_str in enumerate(ep_matches[:10]):
    server = re.search(r'"server"\s*:\s*"([^"]+)"', ep_str)
    name = re.search(r'"name"\s*:\s*"([^"]+)"', ep_str)
    slug = re.search(r'"slug"\s*:\s*"([^"]+)"', ep_str)
    link = re.search(r'"link"\s*:\s*"([^"]+)"', ep_str)
    type_match = re.search(r'"type"\s*:\s*"([^"]+)"', ep_str)
    
    if link:
        media_url = link.group(1)
        is_stream = (media_url.endswith('.m3u8') or '.m3u8' in media_url or 
                     media_url.endswith('.mp4') or '/player/master/' in media_url)
        print(f"Match {idx+1}: Server={server.group(1) if server else 'None'} | Name={name.group(1) if name else 'None'} | Link={media_url[:80]} | is_stream={is_stream}")
