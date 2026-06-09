import sys
import json
import os

# Set stdout/stderr to UTF-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import parse_threads_page from app.py
# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import parse_threads_page

url = "https://www.threads.net/@chipmunk.8255885/post/DZWqikzmsye"
print(f"Testing parse_threads_page with URL: {url}...")
try:
    result = parse_threads_page(url)
    print("\nExtraction Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    if result.get("status") == "success":
        print("\nSuccess! Threads media parsed successfully.")
        print(f"Uploader: {result.get('uploader')}")
        print(f"Images count: {len(result.get('images', []))}")
        print(f"Video Options count: {len(result.get('video_options', []))}")
        print(f"Audio Options count: {len(result.get('audio_options', []))}")
    else:
        print(f"\nFailed to parse: {result.get('message')}")
except Exception as e:
    print(f"\nError occurred during test: {e}")
