import json
import os
import sys

# Add root folder to sys.path so app.py can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

def test_api():
    client = app.test_client()
    url = "https://pin.it/xIWdYUGmi"
    print(f"Calling /api/info with: {url}")
    
    payload = {
        "url": url,
        "client_id": "test_local_pinterest"
    }
    
    response = client.post('/api/info', json=payload)
    print("Status Code:", response.status_code)
    
    try:
        data = response.get_json()
        print("Response JSON:")
        print(json.dumps(data, indent=2))
    except Exception as e:
        print("Failed to get JSON:", e)
        print("Raw response:", response.data)

if __name__ == "__main__":
    test_api()
