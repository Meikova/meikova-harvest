import subprocess

def list_subs():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    command = [
        r"venv\Scripts\yt-dlp.exe",
        "--list-subs",
        url
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        print("Stdout:", result.stdout[:2000])
        print("Stderr:", result.stderr[:2000])
    except Exception as e:
        print("Failed:", e)

if __name__ == "__main__":
    list_subs()
