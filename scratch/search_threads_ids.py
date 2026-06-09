import re
import sys

# Set stdout/stderr to UTF-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

shortcode = "DZWqikzmsye"
username = "chipmunk"

with open("scratch/threads_user_page.html", "r", encoding="utf-8") as f:
    html = f.read()

print("Shortcode occurrences in user page:", len(re.findall(shortcode, html)))
print("Username occurrences in user page:", len(re.findall(username, html)))

# Let's find lines containing the shortcode and print them
lines = html.splitlines()
for idx, line in enumerate(lines):
    if shortcode in line:
        print(f"Line {idx+1} has shortcode (length {len(line)}):")
        pos = line.find(shortcode)
        start = max(0, pos - 150)
        end = min(len(line), pos + 150)
        print("  ...", line[start:end], "...")

    if username in line:
        print(f"Line {idx+1} has username (length {len(line)}):")
        pos = line.find(username)
        start = max(0, pos - 150)
        end = min(len(line), pos + 150)
        print("  ...", line[start:end], "...")
