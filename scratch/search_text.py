import os

search_term = "logged in to the platform"
workspace = r"d:\JOB\DEV\EveryThingDownloader"

print(f"Searching for '{search_term}' in {workspace}...")
found = False
for root, dirs, files in os.walk(workspace):
    if "venv" in root or ".git" in root:
        continue
    for file in files:
        if file.endswith((".py", ".js", ".html", ".css", ".md", ".json")):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if search_term in content:
                        print(f"Found in: {filepath}")
                        found = True
            except Exception as e:
                pass

if not found:
    print("Not found in any source files.")
