import subprocess
import json
import sys

def test_pinterest():
    urls = [
        "https://pin.it/xIWdYUGmi",
        "https://www.pinterest.com/pin/752312312798951024/",
        "https://www.pinterest.com/pin/752312312798951024/sent/?invite_code=7e3f979eca9a4cbf9b6821b29dd3a35b&sender=677017893891828408&sfo=1"
    ]
    
    for url in urls:
        print("\n" + "="*50)
        print(f"Testing gallery-dl for: {url}")
        command = [
            r"venv\Scripts\gallery-dl.exe",
            "--dump-json",
            url
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
            print("Exit Code:", result.returncode)
            if result.stderr:
                print("Stderr:", result.stderr)
            stdout = result.stdout.strip()
            if not stdout:
                print("No output received on stdout.")
                continue
            
            try:
                # Try parsing stdout as one full JSON
                data = json.loads(stdout)
                print("Parsed successfully as one JSON:")
                print(json.dumps(data, indent=2)[:2000])
            except Exception as parse_e:
                print("Failed to parse stdout as one JSON, trying line-by-line:", parse_e)
                lines = stdout.splitlines()
                for line in lines:
                    if line.strip().startswith("["):
                        entry = json.loads(line)
                        print(f"Parsed line: {entry[0]}, {entry[1][:100]}")
        except Exception as e:
            print("Subprocess failed:", e)

if __name__ == "__main__":
    test_pinterest()
