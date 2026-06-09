import sys
import os
sys.path.append(os.path.abspath('.'))

from app import app
import json

client_id = "client_537ngrlf0hnuty574auzds"
url = "https://www.facebook.com/reel/1263752559080744"

with app.test_client() as client:
    print("Testing /api/info for Facebook Reel metadata fallback scraper...")
    resp = client.post('/api/info', json={
        'url': url,
        'client_id': client_id
    })
    
    print("Status Code:", resp.status_code)
    data = resp.get_json()
    if data:
        print("\nExtracted Metadata:")
        print("Title:", data.get("title"))
        print("Views:", data.get("views"))
        print("Likes (Reactions):", data.get("likes"))
        print("Uploader:", data.get("uploader"))
        print("Upload Date:", data.get("upload_date"))
        print("Category:", data.get("category"))
    else:
        print("Failed to get JSON response.")
