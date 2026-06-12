import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import app
from config import TEMP_DOWNLOAD_DIR

client = app.test_client()

# Sample Netscape format cookies text
netscape_text = """# Netscape HTTP Cookie File
# http://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file! Do not edit.

.youtube.com\tTRUE\t/\tTRUE\t2000000000\tLOGIN_INFO\t"some_token_pasted_here"
.youtube.com\tTRUE\t/\tTRUE\t2000000000\tSID\t"sid_value_pasted"
"""

client_id = "test_client_paste_id"

print("Pasting cookies content...")
response = client.post(
    "/api/cookies/paste",
    data=json.dumps({
        "client_id": client_id,
        "content": netscape_text
    }),
    content_type="application/json"
)

print(f"Paste Status Code: {response.status_code}")
data = json.loads(response.data.decode("utf-8"))
print("Paste Response Data:", data)

if response.status_code == 200 and data.get("status") == "success":
    print("✅ SUCCESS: Pasted cookies saved successfully!")
    
    # Check if the file was created and contains the values
    filepath = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")
    if os.path.exists(filepath):
        print("✅ SUCCESS: Saved cookie file exists on disk!")
        with open(filepath, "r", encoding="utf-8") as f:
            saved_content = f.read()
            print("Saved File Content:\n", saved_content)
            if "LOGIN_INFO" in saved_content and "SID" in saved_content:
                print("✅ SUCCESS: Saved content contains parsed cookies!")
            else:
                print("❌ FAILURE: Cookie contents are missing or parsed incorrectly.")
        # Cleanup
        try:
            os.remove(filepath)
        except:
            pass
    else:
        print("❌ FAILURE: Cookie file does not exist on disk.")
else:
    print("❌ FAILURE: Paste endpoint failed.")
