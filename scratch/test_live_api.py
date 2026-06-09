import sys
import os
sys.path.append(os.path.abspath('.'))

from app import app
import json

client_id = "client_537ngrlf0hnuty574auzds"
url = "https://www.facebook.com/stories/729012027223830/UzpfSVNDOjE1MzIxMzM0MDE4MzY2Mzc=/?bucket_count=9&source=story_tray"

# Create a test client
with app.test_client() as client:
    print("Testing /api/info endpoint...")
    response = client.post('/api/info', json={
        'url': url,
        'client_id': client_id
    })
    
    print(f"Status Code: {response.status_code}")
    data = response.get_json()
    print("Response JSON:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
