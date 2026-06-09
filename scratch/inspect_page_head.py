import re
import sys

# Set stdout/stderr to UTF-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

with open("scratch/threads_user_page.html", "r", encoding="utf-8") as f:
    html = f.read()

# Find occurrences of 'robot'
for match in re.finditer(r'robot', html, re.IGNORECASE):
    start = max(0, match.start() - 100)
    end = min(len(html), match.end() + 100)
    print("Found 'robot' context:")
    print("  ...", html[start:end], "...")
