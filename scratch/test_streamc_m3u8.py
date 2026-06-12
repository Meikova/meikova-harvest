import requests
import urllib3
urllib3.disable_warnings()

# Construct the expected stream URL
sub = "eyJoIjoiOTVhYmFiZjhjYzBlMDM3NDFkZWY4NWNlYjgwMGU4MjIiLCJ0IjoiM2EyNzJhZTkxYWU4MGEyODAyMjdhMjUzMTgyNmQwMzQ4ZjMwNGNhZTFhYWUyNmZhMjRjZTQ2MDU1YTQ4ZjUwYSJ9"
m3u8_url = f"https://embed11.streamc.xyz/{sub}.m3u8"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://embed11.streamc.xyz/embed.php?hash=95ababf8cc0e03741def85ceb800e822",
    "Origin": "https://embed11.streamc.xyz"
}

print(f"Fetching stream URL: {m3u8_url}")
resp = requests.get(m3u8_url, headers=headers, verify=False, timeout=10)
print(f"Status Code: {resp.status_code}")
print("Headers:")
for k, v in resp.headers.items():
    print(f"  {k}: {v}")

print("\nResponse Body (first 500 chars):")
print(resp.text[:500])
