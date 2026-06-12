import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

client = app.test_client()

# 1. Test HLS manifest proxying
url_hls = "https://phimchillhd.net/phim/giao-duc-chan-chinh/tap-1_1353070.html" # Just any valid URL that might contain .m3u8, let's test with a simulated URL first
# We can use a public test stream URL for verification
test_url = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"

print(f"Testing HLS proxying on URL: {test_url}")
response = client.get(f"/api/proxy/stream?url={test_url}")
print(f"Status Code: {response.status_code}")
print(f"Content-Type: {response.headers.get('Content-Type')}")
print(f"Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin')}")

# Verify that the relative paths inside the returned manifest have been rewritten to the proxy route
text = response.data.decode("utf-8")
print(f"Manifest sample (first 10 lines):")
lines = text.splitlines()
for line in lines[:10]:
    print(f"  {line}")

has_proxy_rewrites = any("/api/proxy/stream?url=" in line for line in lines)
if has_proxy_rewrites:
    print("[SUCCESS] HLS playlist relative links rewritten to proxy endpoints successfully!")
else:
    print("[FAILED] Relative links were not rewritten.")

# 2. Test binary streaming proxying
test_binary_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
print(f"\nTesting Binary Video proxying on URL: {test_binary_url}")
response_binary = client.get(f"/api/proxy/stream?url={test_binary_url}")
print(f"Status Code: {response_binary.status_code}")
print(f"Content-Type: {response_binary.headers.get('Content-Type')}")
print(f"Content-Length: {response_binary.headers.get('Content-Length')}")
print(f"Accept-Ranges: {response_binary.headers.get('Accept-Ranges')}")

if response_binary.status_code == 200 and "video/mp4" in response_binary.headers.get('Content-Type', '').lower():
    print("[SUCCESS] Binary video streaming proxy initiated successfully!")
else:
    print("[FAILED] Binary video streaming proxy failed.")
