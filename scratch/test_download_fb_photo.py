import requests
import json
import time

url = "http://127.0.0.1:5000/api/download"
# Use the first photo URL from our previous test
photo_url = "https://scontent.fsgn5-11.fna.fbcdn.net/v/t39.30808-6/717140297_122139628731129808_6188801803449636060_n.jpg?stp=dst-jpg_tt6&cstp=mx1366x2048&ctp=s1366x2048&_nc_cat=110&ccb=1-7&_nc_sid=833d8c&_nc_ohc=px_Sps577FwQ7kNvwGKIV72&_nc_oc=AdqEhHe-bcs5aK_q2BctrlpeZyJ8LeiAwSCbTSYODBQYUnJ3kcbt4UUH9fpXZljpH8denn2gY3FXaAOyvLZ9D3xs&_nc_zt=23&_nc_ht=scontent.fsgn5-11.fna&_nc_gid=o7g3UfBu4CSJX-Pk4qVDpQ&_nc_ss=7b20f&oh=00_Af9sR6kKgMPVqdl4ISp_MgYbYqhiV2H3os3x_9_yQbt23A&oe=6A2DE1B6"

payload = {
    "url": photo_url,
    "format_id": "direct_photo_1",
    "ext": "jpg",
    "title": "Hoàng hôn đẹp nhất",
    "client_id": "client_537ngrlf0hnuty574auzds"
}

print("Initiating direct photo download task...")
r = requests.post(url, json=payload)
print(f"Status Code: {r.status_code}")
res = r.json()
print(json.dumps(res, indent=2))

if res.get("status") == "success":
    download_id = res["download_id"]
    status_url = f"http://127.0.0.1:5000/api/download/status/{download_id}"
    
    # Poll status
    for i in range(10):
        print(f"\nChecking status (attempt {i+1})...")
        r_status = requests.get(status_url)
        status_data = r_status.json()
        print(json.dumps(status_data, indent=2))
        
        if status_data.get("status") == "complete":
            print("Download task completed successfully!")
            break
        elif status_data.get("status") == "error":
            print("Download task failed!")
            break
            
        time.sleep(2)
