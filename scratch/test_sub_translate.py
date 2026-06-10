import subprocess
import os

def test_subs():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    attempts = [
        ["--write-auto-sub", "--sub-langs", "orig->vi", "--skip-download"],
        ["--write-auto-sub", "--sub-langs", "en->vi", "--skip-download"],
        ["--write-auto-sub", "--sub-langs", "vi-en", "--skip-download"],
        ["--write-auto-sub", "--sub-langs", "vi", "--skip-download"],
    ]
    
    for idx, opts in enumerate(attempts):
        print(f"\n--- Attempt {idx+1}: {' '.join(opts)} ---")
        command = [
            r"venv\Scripts\yt-dlp.exe",
            *opts,
            url
        ]
        
        try:
            temp_test_dir = f"temp_sub_test_{idx}"
            os.makedirs(temp_test_dir, exist_ok=True)
            
            result = subprocess.run(
                command, 
                cwd=temp_test_dir,
                capture_output=True, 
                text=True, 
                encoding="utf-8", 
                errors="ignore"
            )
            print("Exit Code:", result.returncode)
            print("Stdout:", result.stdout[:500])
            print("Stderr:", result.stderr[:500])
            
            files = os.listdir(temp_test_dir)
            print("Downloaded files:", files)
            
            # Clean up
            for f in files:
                os.remove(os.path.join(temp_test_dir, f))
            os.rmdir(temp_test_dir)
            
        except Exception as e:
            print("Failed:", e)

if __name__ == "__main__":
    test_subs()
