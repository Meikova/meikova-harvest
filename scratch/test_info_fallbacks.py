import sys
sys.path.append('.')
import json
from app import app

def test_url(url):
    print(f"\n--- Testing URL: {url} ---")
    with app.test_client() as client:
        res = client.post('/api/info', json={'url': url, 'client_id': 'test_client'})
        print(f"Status Code: {res.status_code}")
        try:
            data = json.loads(res.data.decode('utf-8'))
            print("Response JSON:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Failed to parse response: {e}")
            print(res.data)

if __name__ == '__main__':
    # Test Twitter URL (without cookies, which is expected to return the login cookie requirement message)
    test_url('https://x.com/NASA/status/1682845876543')
    
    # Test SoundCloud URL (which is expected to return the geo-restriction message)
    test_url('https://soundcloud.com/octobersveryown/drake-back-to-back')
