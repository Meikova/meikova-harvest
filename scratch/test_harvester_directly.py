import sys
import os
# Add root path to sys.path to allow importing routes.info
sys.path.append(os.getcwd())

import logging
logging.basicConfig(level=logging.INFO)

from routes.info import generic_html_link_harvester

url = "https://motchilltv.lt/episodes/bai-hoc-dang-doi-tap-1/"
print("Calling generic_html_link_harvester...")
res = generic_html_link_harvester(url, "test-client")
import json
print("\n--- RESULT ---")
if res:
    print("Success! Writing result to scratch/harvester_direct_res.json")
    with open("scratch/harvester_direct_res.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
else:
    print("Failed: Returned None")
