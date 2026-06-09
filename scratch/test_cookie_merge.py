import requests
import json

base_url = "http://127.0.0.1:5000"
client_id = "client_test_merge"

# Clean up any existing cookie file first
requests.post(f"{base_url}/api/cookies/clear/{client_id}")

print("1. Checking initial cookie status (should be empty/False)...")
r = requests.get(f"{base_url}/api/cookies/status/{client_id}")
print(r.json())

# Sample J2TEAM JSON cookies for Instagram
ig_cookies = {
    "cookies": [
        {
            "domain": ".instagram.com",
            "expirationDate": 1813021450,
            "name": "mid",
            "path": "/",
            "secure": True,
            "value": "agErDQALAAHzEb6QIu1ceRhyXk8J"
        }
    ]
}

print("\n2. Uploading Instagram cookies...")
files = {
    "file": ("cookies_ig.json", json.dumps(ig_cookies), "application/json")
}
data = {
    "client_id": client_id
}
r = requests.post(f"{base_url}/api/cookies/upload", data=data, files=files)
print(r.json())

print("\n3. Checking cookie status (should list Instagram)...")
r = requests.get(f"{base_url}/api/cookies/status/{client_id}")
status_data = r.json()
print(status_data)
assert "Instagram" in status_data.get("domains", [])

# Sample J2TEAM JSON cookies for YouTube
yt_cookies = {
    "cookies": [
        {
            "domain": ".youtube.com",
            "expirationDate": 1796561668,
            "name": "VISITOR_INFO1_LIVE",
            "path": "/",
            "secure": True,
            "value": "Dry7JhhSNkU"
        }
    ]
}

print("\n4. Uploading YouTube cookies (should merge)...")
files = {
    "file": ("cookies_yt.json", json.dumps(yt_cookies), "application/json")
}
r = requests.post(f"{base_url}/api/cookies/upload", data=data, files=files)
print(r.json())

print("\n5. Checking cookie status (should list both Instagram and YouTube)...")
r = requests.get(f"{base_url}/api/cookies/status/{client_id}")
status_data = r.json()
print(status_data)
assert "Instagram" in status_data.get("domains", [])
assert "YouTube" in status_data.get("domains", [])

print("\n6. Clearing cookies...")
r = requests.post(f"{base_url}/api/cookies/clear/{client_id}")
print(r.json())

print("\n7. Checking final cookie status (should be empty)...")
r = requests.get(f"{base_url}/api/cookies/status/{client_id}")
print(r.json())
assert r.json().get("has_cookies") == False

print("\nAll cookie merge tests passed successfully!")
