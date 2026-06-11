import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import app

client = app.test_client()

# Use an unsupported URL to trigger the Unsupported URL error
url = "https://www.pinterest.com/?show_error=true"
client_id = "client_lvnnn0l2zy8d6g9idw3j9a"

print(f"Sending request with URL: {url}")
response = client.post(
    "/api/info",
    data=json.dumps({"url": url, "client_id": client_id}),
    content_type="application/json"
)

print(f"Status Code: {response.status_code}")
try:
    data = json.loads(response.data.decode("utf-8"))
    message = data.get("message", "")
    print(f"Response Message: {message}")
    
    # Check if any ANSI escape codes exist in the message
    # ANSI escape code starts with \x1b or \033
    contains_ansi = "\x1b" in message or "\033" in message or "[0;31m" in message
    print(f"Contains ANSI escape codes: {contains_ansi}")
    if not contains_ansi:
        print("✅ Success! ANSI escape codes have been successfully stripped.")
    else:
        print("❌ Failed! ANSI escape codes are still present.")
except Exception as e:
    print("Error parsing response:", e)
    print("Raw response:", response.data)
