with open("scratch/fb_externalhit.html", "r", encoding="utf-8") as f:
    html = f.read()

target = "122139628731129808"
pos = 0
while True:
    pos = html.find(target, pos)
    if pos == -1:
        break
    print(f"\n--- Match at index {pos} ---")
    start = max(0, pos - 150)
    end = min(len(html), pos + 150)
    print(html[start:end])
    pos += len(target)
