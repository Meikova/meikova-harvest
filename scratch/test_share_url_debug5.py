import sys, os, re, json, subprocess, urllib.parse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from config import TEMP_DOWNLOAD_DIR

url = "https://www.facebook.com/share/v/18fgW8Tbvc/"

cookies_dir = os.path.join(TEMP_DOWNLOAD_DIR, "cookies")
cookie_file = os.path.join(cookies_dir, "cookies_client_lvnnn0l2zy8d6g9idw3j9a.txt")

command = [
    "curl", "-s", "-L",
    "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "-H", "Accept-Language: vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "-H", "Sec-Fetch-Mode: navigate",
    "-H", "Upgrade-Insecure-Requests: 1",
    "-b", cookie_file,
]
command.append(url)

result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
html = result.stdout

print(f"HTML length: {len(html)}")

# Strategy: Extract the share token from the URL
share_token = None
share_match = re.search(r'/share/[vp]/([^/?#]+)', url)
if share_match:
    share_token = share_match.group(1)
    print(f"Share token: {share_token}")

# Find all occurrences of this token in the HTML and extract context
if share_token:
    # Look for share_url containing this token - decode it as it might be URL-encoded
    # Pattern: share_url=https%3A%2F%2F...share%2Fv%2F{token}
    # Or: share/v/{token}
    
    # First, find permalink or post URL near the token
    all_matches = list(re.finditer(re.escape(share_token), html))
    print(f"Token appears {len(all_matches)} times in HTML")
    
    for i, match in enumerate(all_matches[:5]):
        start = max(0, match.start() - 300)
        end = min(len(html), match.end() + 300)
        context = html[start:end]
        
        # Try to find post_id or permalink near this context
        permalink_ids = re.findall(r'permalink/(\d+)', context)
        post_ids = re.findall(r'"post_id"\s*:\s*"(\d+)"', context)
        
        print(f"\nMatch {i+1} at position {match.start()}:")
        if permalink_ids:
            print(f"  Nearby permalink IDs: {permalink_ids}")
        if post_ids:
            print(f"  Nearby post_ids: {post_ids}")
        
        # Show a short snippet
        snippet = context.replace('\n', ' ')[:200]
        print(f"  Context: ...{snippet}...")

# Strategy 2: Find route info - look for initialRouteInfo
route_match = re.search(r'"initialRouteInfo"\s*:\s*\{[^}]*"url"\s*:\s*"([^"]+)"', html)
if route_match:
    route_url = route_match.group(1).replace("\\/", "/").replace("\\u00253A", ":").replace("\\u00252F", "/")
    print(f"\nRoute URL: {route_url}")
    # Extract post_id from route URL
    perm = re.search(r'/permalink/(\d+)', route_url)
    if perm:
        print(f"Post ID from route: {perm.group(1)}")

# Strategy 3: Look for the URL pattern /groups/*/permalink/POSTID/ near the share token
scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
for i, s in enumerate(scripts):
    if share_token not in s:
        continue
    # Found the script with our token
    # Find the route/url that contains permalink
    route_urls = re.findall(r'"url"\s*:\s*"([^"]*permalink[^"]*)"', s)
    for ru in route_urls:
        decoded = ru.replace("\\/", "/").replace("\\u00253A", ":").replace("\\u00252F", "/").replace("\\u0025", "%")
        decoded = urllib.parse.unquote(decoded)
        print(f"\nPermalink URL in script {i}: {decoded}")
        perm = re.search(r'/permalink/(\d+)', decoded)
        if perm:
            print(f"  -> Post ID: {perm.group(1)}")
    break
