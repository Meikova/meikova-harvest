import json
import os
import sys
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

# Ensure output is utf-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 1. Parse JSON cookies
json_path = "downloads/cookies/www.youtube.com_10-06-2026.json"
netscape_path = "scratch/user_cookies_netscape.txt"

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

cookies_list = data.get("cookies") or []
print(f"Loaded {len(cookies_list)} cookies from JSON.")

# Convert to Netscape format
lines = [
    "# Netscape HTTP Cookie File",
    "# http://curl.haxx.se/rfc/cookie_spec.html",
    "# This is a generated file!  Do not edit.",
    ""
]
for cookie in cookies_list:
    domain = cookie.get("domain", "")
    if not domain:
        continue
    path = cookie.get("path", "/")
    secure = "TRUE" if cookie.get("secure", False) else "FALSE"
    expiration = str(int(cookie.get("expirationDate") or 0))
    flag = "TRUE" if domain.startswith(".") else "FALSE"
    name = cookie.get("name", "")
    value = cookie.get("value", "")
    lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}")

with open(netscape_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"Converted and saved to {netscape_path}")

# 2. Test different player clients
url = "https://www.youtube.com/watch?v=eBm23CzA-w4"

client_combinations = [
    ["default", "-tv", "-tv_downgraded"],
    ["default"],
    ["web"],
    ["mweb"],
    ["android", "ios"],
    ["android_vr"]
]

for idx, clients in enumerate(client_combinations):
    print(f"\n--- Test {idx}: player_client={clients} ---")
    ydl_opts = {
        "verbose": True,
        "quiet": False,
        "no_warnings": False,
        "nocheckcertificate": True,
        "noplaylist": True,
        "cookiefile": netscape_path,
        "js_runtimes": {"node": {}},
        "impersonate": ImpersonateTarget.from_str("chrome") if ImpersonateTarget else None,
        "extractor_args": {
            "youtube": {
                "player_client": clients,
            }
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])
            print(f"Success! Extracted {len(formats)} formats.")
            for f in formats[:3]:
                print(f"  Format: {f.get('format_id')} - {f.get('resolution')} ({f.get('ext')})")
    except Exception as e:
        print(f"Failed: {e}")
