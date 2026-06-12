import requests
import urllib3
urllib3.disable_warnings()

url_ajax = "https://motchilltv.lt/wp-admin/admin-ajax.php"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "https://motchilltv.lt/episodes/bai-hoc-dang-doi-tap-1/"
}

# Test for nume 1, 2, 3
for nume in [1, 2, 3]:
    data = {
        "action": "doo_player_ajax",
        "post": "32782",
        "nume": str(nume),
        "type": "tv"
    }
    
    print(f"\n--- Testing nume={nume} ---")
    try:
        resp = requests.post(url_ajax, headers=headers, data=data, verify=False, timeout=10)
        print(f"Status Code: {resp.status_code}")
        print("Response JSON:")
        print(resp.json())
    except Exception as e:
        print(f"Request failed: {e}")
