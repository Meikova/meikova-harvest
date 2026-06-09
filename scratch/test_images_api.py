import sys
import os
sys.path.append(os.path.abspath('.'))

from app import app
import json

client_id = "client_537ngrlf0hnuty574auzds"
# Test single image proxy
img_url = "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=100"
filename = "test_image.jpg"

with app.test_client() as client:
    print("Testing /api/download/image proxy...")
    resp = client.get(f'/api/download/image?url={img_url}&filename={filename}')
    print("Proxy Status Code:", resp.status_code)
    print("Proxy Headers:", dict(resp.headers))
    
    print("\nTesting /api/download/images/zip...")
    post_data = {
        "title": "test_album",
        "urls": [
            {"url": img_url, "label": "Image 1", "ext": "jpg"},
            {"url": img_url, "label": "Image 2", "ext": "jpg"}
        ]
    }
    resp_zip = client.post('/api/download/images/zip', json=post_data)
    print("ZIP Status Code:", resp_zip.status_code)
    print("ZIP Headers:", dict(resp_zip.headers))
    print("ZIP File size:", len(resp_zip.data), "bytes")
