import subprocess
import json

def dump_pinterest():
    url = "https://www.pinterest.com/pin/752312312798951024/"
    command = [
        r"venv\Scripts\gallery-dl.exe",
        "--dump-json",
        url
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        stdout = result.stdout.strip()
        data = json.loads(stdout)
        
        print(f"Total entries: {len(data)}")
        for i, entry in enumerate(data):
            print(f"\nEntry {i+1}:")
            print(f"  Type: {entry[0]}")
            if entry[0] == 1 or isinstance(entry[1], str):
                print(f"  Value (URL/Path): {entry[1]}")
            if len(entry) >= 3 and isinstance(entry[2], dict):
                meta = entry[2]
                print("  Metadata subset:")
                for k in ["title", "description", "id", "image", "images", "videos", "video", "creator", "username", "category", "subcategory", "ext", "extension"]:
                    if k in meta:
                        print(f"    {k}: {meta[k]}")
                # Print image details if present
                if "images" in meta:
                    print("    images detail:", json.dumps(meta["images"], indent=2)[:500])
                if "videos" in meta:
                    print("    videos detail:", json.dumps(meta["videos"], indent=2)[:500])
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    dump_pinterest();
