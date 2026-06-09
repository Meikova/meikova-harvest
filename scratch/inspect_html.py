html_path = "d:/JOB/DEV/EveryThingDownloader/scratch/story.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

print("File size:", len(html))

# Check for name
for term in ["Joshua", "Platillero", "login", "cookie", "Facebook", "story", "stories", "Security", "checkpoint"]:
    count = html.lower().count(term.lower())
    print(f"Term '{term}': {count} occurrences")

# Print first 1000 characters and last 1000 characters
print("\n--- FIRST 1000 CHARACTERS ---")
print(html[:1000])

print("\n--- LAST 1000 CHARACTERS ---")
print(html[-1000:])
