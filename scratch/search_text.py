import os

def search():
    target = b"Embedding soft subtitles"
    for root, dirs, files in os.walk("."):
        # skip git and venv
        if ".git" in root or "venv" in root:
            continue
        for file in files:
            path = os.path.join(root, file)
            try:
                with open(path, "rb") as f:
                    content = f.read()
                    if target in content:
                        print(f"Found in: {path}")
            except Exception:
                pass

if __name__ == "__main__":
    search()
