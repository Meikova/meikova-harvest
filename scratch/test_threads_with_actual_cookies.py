import requests
import json
import sys
import os
import http.cookiejar
import re


# Set stdout/stderr to UTF-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def shortcode_to_post_id(shortcode):
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
    post_id = 0
    for char in shortcode:
        post_id = post_id * 64 + alphabet.index(char)
    return str(post_id)

shortcode = "DZWqikzmsye"
post_id = shortcode_to_post_id(shortcode)
print(f"Shortcode: {shortcode} -> Post ID: {post_id}")

# Find cookie file
cookies_dir = "downloads/cookies"
cookie_files = [f for f in os.listdir(cookies_dir) if f.startswith("cookies_") and f.endswith(".txt")]
if not cookie_files:
    print("No cookie files found in downloads/cookies")
    sys.exit(1)

cookie_file = os.path.join(cookies_dir, cookie_files[0])
print(f"Using cookie file: {cookie_file}")

session = requests.Session()

# Load netscape cookies
cookie_jar = http.cookiejar.MozillaCookieJar()
try:
    cookie_jar.load(cookie_file, ignore_discard=True, ignore_expires=True)
    session.cookies.update(cookie_jar)
    print(f"Loaded {len(session.cookies)} cookies from file.")
    
    # Replicate cookies to Threads domains
    replicated_count = 0
    for cookie in list(session.cookies):
        domain = getattr(cookie, 'domain', '')
        if 'instagram.com' in domain or 'instagr.am' in domain or 'facebook.com' in domain:
            for target_domain in ['.threads.net', '.threads.com', 'www.threads.net', 'threads.net', 'threads.com']:
                new_cookie = requests.cookies.create_cookie(
                    name=cookie.name,
                    value=cookie.value,
                    domain=target_domain,
                    path=cookie.path,
                    secure=cookie.secure,
                    expires=cookie.expires
                )
                session.cookies.set_cookie(new_cookie)
                replicated_count += 1
    print(f"Replicated {replicated_count} cookies to Threads domains.")
except Exception as e:
    print(f"Error loading cookies: {e}")

# First fetch post page anonymously to get LSD token
post_url = f"https://www.threads.net/@chipmunk.8255885/post/{shortcode}"
print(f"Fetching post page anonymously: {post_url}...")
anon_session = requests.Session()
main_res = anon_session.get(post_url, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}, allow_redirects=True)
print("Anon Post page status:", main_res.status_code)
print("Anon Final response URL:", main_res.url)

# Extract lsd from page if present
lsd = "AVoP_VzN1W0" # default fallback
lsd_match = re.search(r'"LSD",\[\],\{"token":"([^"]+)"\}', main_res.text)
if lsd_match:
    lsd = lsd_match.group(1)
    print("Found LSD token:", lsd)
else:
    lsd_match = re.search(r'"lsd":"([^"]+)"', main_res.text)
    if lsd_match:
        lsd = lsd_match.group(1)
        print("Found LSD token (alt):", lsd)
    else:
        print("LSD token not found. Using default.")

# Now prepare authenticated GraphQL POST using session with cookies
graphql_url = "https://www.threads.com/api/graphql"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "x-ig-app-id": "238260118697367",
    "Content-Type": "application/x-www-form-urlencoded",
    "x-fb-lsd": lsd,
    "Origin": "https://www.threads.com",
    "Referer": post_url.replace("threads.net", "threads.com")
}




data = {
    "lsd": lsd,
    "variables": json.dumps({"postID": post_id}),
    "doc_id": "5587632691339264"
}

print("Posting to GraphQL API...")
res = session.post(graphql_url, headers=headers, data=data, timeout=15)
print("GraphQL status code:", res.status_code)
print("Content-Type:", res.headers.get("Content-Type"))

if "application/json" in res.headers.get("Content-Type", ""):
    resp_json = res.json()
    print("Success! JSON received.")
    with open("scratch/threads_api_response_actual.json", "w", encoding="utf-8") as f:
        json.dump(resp_json, f, indent=2, ensure_ascii=False)
    print("Response saved to scratch/threads_api_response_actual.json")
else:
    print("Response text:", res.text[:2000])
