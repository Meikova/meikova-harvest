import subprocess
import json
import sys

def test_gallery_dl():
    url = "https://www.instagram.com/p/DY4UckRBiTU/"
    print(f"Testing gallery-dl for: {url}")
    
    # We call gallery-dl with --dump-json
    command = [
        r"venv\Scripts\gallery-dl.exe",
        "--dump-json",
        url
    ]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        print("Exit Code:", result.returncode)
        
        # Check stderr
        if result.stderr:
            print("Stderr:", result.stderr)
            
        stdout = result.stdout.strip()
        if not stdout:
            print("No output received on stdout.")
            return
            
        print("Successfully received output. Attempting to parse JSON...")
        # gallery-dl prints one JSON array or JSON objects separated by newline
        # Let's inspect the stdout
        try:
            # Let's parse it. Sometimes it's a JSON array, sometimes it's multiple JSON arrays separated by newlines
            lines = stdout.splitlines()
            entries = []
            for line in lines:
                if line.strip().startswith("["):
                    entry = json.loads(line)
                    entries.append(entry)
            
            print(f"Parsed {len(entries)} media entries from gallery-dl:")
            for idx, entry in enumerate(entries):
                print(f"Entry {idx+1}:")
                print(f"  Type number: {entry[0]}")
                print(f"  Media URL: {entry[1][:100]}...")
                # print(f"  Metadata: {list(entry[2].keys())}")
        except Exception as parse_e:
            print("Failed to parse output as JSON:", parse_e)
            print("Raw output preview:", stdout[:1000])
            
    except Exception as e:
        print("Subprocess failed:", e)

if __name__ == "__main__":
    test_gallery_dl()
