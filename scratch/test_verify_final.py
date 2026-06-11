import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import app

# Set up test client
client = app.test_client()

urls = [
    ("share/v", "https://www.facebook.com/share/v/18fgW8Tbvc/"),
    ("reel", "https://www.facebook.com/reel/769241986206453"),
]

client_id = "client_lvnnn0l2zy8d6g9idw3j9a"

for label, url in urls:
    print(f"\n==================== Testing API: {label} ====================")
    print(f"URL: {url}")
    
    response = client.post(
        "/api/info",
        data=json.dumps({"url": url, "client_id": client_id}),
        content_type="application/json"
    )
    
    print(f"Response Status Code: {response.status_code}")
    try:
        data = json.loads(response.data.decode("utf-8"))
        if response.status_code == 200:
            print(f"✅ Success!")
            print(f"  Title:       {data.get('title')}")
            print(f"  Uploader:    {data.get('uploader')}")
            print(f"  Duration:    {data.get('duration')} seconds")
            print(f"  Upload Date: {data.get('upload_date')}")
            print(f"  Thumbnail:   {'YES' if data.get('thumbnail') else 'NO'}")
            print(f"  Views:       {data.get('views')}")
            print(f"  Likes:       {data.get('likes')}")
            
            video_options = data.get('video_options', [])
            print(f"  Video Options Count: {len(video_options)}")
            for idx, opt in enumerate(video_options[:3]):
                print(f"    Option {idx}: Label={opt.get('label')}, Size={opt.get('size')}, Res={opt.get('resolution')}")
        else:
            print(f"❌ Error: {data.get('message')}")
    except Exception as parse_err:
        print(f"❌ Failed to parse response JSON: {parse_err}")
        print(f"Raw response: {response.data}")
