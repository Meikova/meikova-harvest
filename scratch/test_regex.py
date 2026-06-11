import re
import os

vtt_path = r"D:\JOB\DEV\EveryThingDownloader\downloads\temp_0c335efe-1922-43ca-9347-7e9d9d36c960\media.vi.vtt"

with open(vtt_path, 'r', encoding='utf-8') as f:
    content = f.read()

pattern = r"((?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})\s*-->\s*((?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})[^\r\n]*\r?\n(.*?)(?=\r?\n(?:\d{2}:)?\d{2}:\d{2}[.,]\d{3}|\Z)"
matches = list(re.finditer(pattern, content, re.DOTALL))

print(f"Total matches found: {len(matches)}")
if matches:
    print("First 3 matches:")
    for idx, m in enumerate(matches[:3]):
        print(f"Match {idx+1}: Start={m.group(1)}, End={m.group(2)}, Text={repr(m.group(3))}")
