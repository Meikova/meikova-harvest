import requests
import re
import json

url = "https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256/tap-1"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
resp = requests.get(url, headers=headers, verify=False, timeout=15)
html = resp.text

# Clean up backslashes
clean_html = html.replace('\\/', '/').replace('\\', '')

episode_pattern = r'\{[^{}]*"server"[^{}]*"name"[^{}]*"slug"[^{}]*"link"[^{}]*\}'
ep_matches = re.findall(episode_pattern, clean_html)

parsed_episodes = []
for ep_str in ep_matches:
    try:
        if not ep_str.startswith('{'): ep_str = '{' + ep_str
        if not ep_str.endswith('}'): ep_str = ep_str + '}'
        
        server = re.search(r'"server"\s*:\s*"([^"]+)"', ep_str)
        name = re.search(r'"name"\s*:\s*"([^"]+)"', ep_str)
        slug = re.search(r'"slug"\s*:\s*"([^"]+)"', ep_str)
        link = re.search(r'"link"\s*:\s*"([^"]+)"', ep_str)
        
        parsed_episodes.append({
            "raw": ep_str,
            "server": server.group(1) if server else None,
            "name": name.group(1) if name else None,
            "slug": slug.group(1) if slug else None,
            "link": link.group(1) if link else None
        })
    except Exception as e:
        parsed_episodes.append({"error": str(e), "raw": ep_str})

with open("scratch/all_parsed_episodes.json", "w", encoding="utf-8") as f:
    json.dump(parsed_episodes, f, indent=2, ensure_ascii=False)

print(f"Dumped {len(parsed_episodes)} objects to scratch/all_parsed_episodes.json")
