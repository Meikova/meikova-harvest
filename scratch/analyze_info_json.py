import json

with open("scratch/tiktok_info.json", "r", encoding="utf-8") as f:
    info = json.load(f)

print("Keys in info:", list(info.keys()))

# Check thumbnails
thumbnails = info.get("thumbnails") or []
print(f"Thumbnails count: {len(thumbnails)}")
for idx, t in enumerate(thumbnails):
    print(f"  Thumb {idx}:")
    for k, v in t.items():
        print(f"    {k}: {str(v)[:100]}...")

# Look for any keys containing the word 'url' or 'image' or 'photo' or 'thumb'
for k, v in info.items():
    if any(x in k.lower() for x in ["url", "image", "photo", "thumb"]):
        print(f"Key '{k}': {str(v)[:150]}...")

# Check inside formats
formats = info.get("formats") or []
print(f"Formats count: {len(formats)}")
for idx, f in enumerate(formats):
    print(f"  Format {idx} ID: {f.get('format_id')}")
    print(f"    Note: {f.get('format_note')}")
    print(f"    URL: {f.get('url')[:100]}...")
    print(f"    vcodec: {f.get('vcodec')}")
