import requests

url = "http://127.0.0.1:5000/"
try:
    res = requests.get(url, timeout=10)
    print("Server response status code:", res.status_code)
    if res.status_code == 200:
        print("Success! EveryThingDownloader index is loaded successfully.")
    else:
        print("Error: Server returned status code", res.status_code)
except Exception as e:
    print("Failed to contact server:", e)
