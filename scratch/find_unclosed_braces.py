with open("d:/JOB/DEV/EveryThingDownloader/static/css/styles.css", "r", encoding="utf-8") as f:
    content = f.read()

stack = []
for idx, char in enumerate(content):
    if char == '{':
        stack.append(idx)
    elif char == '}':
        if not stack:
            print(f"Extra closing brace at char {idx}")
        else:
            stack.pop()

if stack:
    print(f"There are {len(stack)} unclosed opening braces!")
    for start in stack:
        # Get line number of start
        line_num = content[:start].count('\n') + 1
        snippet = content[start:start+100].replace('\n', ' ')
        print(f"Unclosed opening brace at line {line_num}: {snippet}")
else:
    print("All braces are properly closed!")
