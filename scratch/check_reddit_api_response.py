import sys
import os
sys.path.append(os.getcwd())

import json
from app import app

client = app.test_client()

url = "https://www.reddit.com/r/ArtificialInteligence/s/bX7TYEv45P"

print("Querying backend for URL:", url)
response = client.post('/api/info', json={
    "url": url,
    "client_id": "test_client" # Let's see if we have cookies there, but wait, we can just test with no client cookies first, or look at what it returned.
})

print("Response status code:", response.status_code)
try:
    data = json.loads(response.data)
    print("Response JSON:")
    print("Title:", data.get("title"))
    print("Thumbnail URL:", data.get("thumbnail"))
    print("Images count:", len(data.get("images", [])))
    if data.get("images"):
        print("First image:", data.get("images")[0])
except Exception as e:
    print("Failed to parse response:", e)
    print("Raw response:", response.data[:1000])
