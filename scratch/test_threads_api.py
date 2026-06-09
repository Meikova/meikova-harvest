import requests
import json
import sys

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

# 1. Test with the user's shortcode: DZWqikzmsye
shortcode = "DZWqikzmsye"
post_id = shortcode_to_post_id(shortcode)
print(f"Testing shortcode: {shortcode} -> Post ID: {post_id}")

url = "https://www.threads.net/api/graphql"
headers = {
    "User-Agent": "threads-client",
    "x-ig-app-id": "238260118697367",
    "Content-Type": "application/x-www-form-urlencoded"
}

data = {
    "variables": json.dumps({"postID": post_id}),
    "doc_id": "5587632691339264"
}

try:
    response = requests.post(url, headers=headers, data=data, timeout=15)
    print("Status code:", response.status_code)
    print("Content-type:", response.headers.get("Content-Type"))
    
    if "application/json" in response.headers.get("Content-Type", ""):
        resp_json = response.json()
        print("Success! Response is JSON.")
        with open("scratch/threads_api_response_direct.json", "w", encoding="utf-8") as f:
            json.dump(resp_json, f, indent=2, ensure_ascii=False)
        print("Saved to scratch/threads_api_response_direct.json")
        print("Response preview:", str(resp_json)[:1000] + "...")
    else:
        print("Response text:", response.text[:500])
except Exception as e:
    print("Request failed:", e)
