import json
import re
import sys

# Set stdout/stderr to UTF-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

with open("scratch/threads_facebookexternalhit.html", "r", encoding="utf-8") as f:
    html = f.read()

scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
print("Found scripts count:", len(scripts))

for idx, script in enumerate(scripts):
    try:
        data = json.loads(script)
        # Search recursively for any string containing 'scontent' or 'cdninstagram'
        urls = []
        def search_for_strings(d):
            if isinstance(d, dict):
                for k, v in d.items():
                    if isinstance(v, str) and ('scontent' in v or 'cdninstagram' in v):
                        urls.append((k, v))
                    elif isinstance(v, (dict, list)):
                        search_for_strings(v)
            elif isinstance(d, list):
                for item in d:
                    search_for_strings(item)
                    
        search_for_strings(data)
        if urls:
            print(f"\n--- Script {idx+1} has CDNs (length: {len(script)}) ---")
            for k, u in urls[:5]:
                print(f"  {k}: {u[:120]}...")
            if len(urls) > 5:
                print(f"  ... and {len(urls) - 5} more")
    except Exception as e:
        pass
