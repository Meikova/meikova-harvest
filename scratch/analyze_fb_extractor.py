with open('venv/Lib/site-packages/yt_dlp/extractor/facebook.py', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'like_count' in line or 'likes' in line or 'reaction' in line:
        start = max(0, i - 2)
        end = min(len(lines), i + 3)
        print(f"\n--- Line {i+1} ---")
        for idx in range(start, end):
            print(f"{idx+1}: {lines[idx].strip()}")
