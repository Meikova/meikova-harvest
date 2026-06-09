import sys
import os
sys.path.append(os.path.abspath('.'))

from app import app, get_info
import json

url = "https://www.facebook.com/FuzeTeaVN/videos/1305800194990596/?rdid=MPAnduUW537wyGJ4#"
client_id = "client_537ngrlf0hnuty574auzds"

with app.test_request_context(
    path='/api/info',
    method='POST',
    data=json.dumps({"url": url, "client_id": client_id}),
    headers={'Content-Type': 'application/json'}
):
    print("Calling get_info()...")
    try:
        response = get_info()
        print("Status code:", response[1] if isinstance(response, tuple) else response.status_code)
        body = response[0].get_data(as_text=True) if isinstance(response, tuple) else response.get_data(as_text=True)
        print("JSON Response:")
        print(json.dumps(json.loads(body), indent=2))
    except Exception as e:
        import traceback
        traceback.print_exc()
