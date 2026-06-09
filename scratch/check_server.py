import urllib.request
import json

url = "http://127.0.0.1:5000/api/info"
payload = {
    "url": "https://www.facebook.com/FuzeTeaVN/videos/1305800194990596/?rdid=MPAnduUW537wyGJ4#",
    "client_id": "537ngrlf0hnuty574auzds"
}

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)

try:
    with urllib.request.urlopen(req) as response:
        status = response.getcode()
        body = response.read().decode('utf-8')
        print("Server is RUNNING!")
        print("Status:", status)
        print("Response:", body)
except Exception as e:
    print("Server request failed:", e)
    print("This means the server is either stopped or returned an error.")
