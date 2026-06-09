import json
import sys

# Reconfigure stdout to use UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

log_path = r"C:\Users\kiemp\.gemini\antigravity\brain\cb3ca4a1-8ddb-4f06-b457-3ae83cb6e20b\.system_generated\logs\transcript.jsonl"
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        step = data.get("step_index", 0)
        if 3181 <= step <= 3215:
            print(f"=== STEP {step} ({data.get('source')} - {data.get('type')}) ===")
            if "content" in data and data["content"]:
                print("Content:", data["content"])
            if "tool_calls" in data and data["tool_calls"]:
                print("Tool Calls:", data["tool_calls"])
