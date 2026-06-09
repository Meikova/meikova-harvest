import re
import os

dump_file = "1263752559080744_https_-_www.facebook.com_watch_v=1263752559080744__rdr.dump"
if not os.path.exists(dump_file):
    # Try searching in scratch or root
    print("File not found in root, checking list of files.")
    for f in os.listdir('.'):
        if '1263752559080744' in f:
            dump_file = f
            print("Found file:", dump_file)
            break

with open(dump_file, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

print("Dump length:", len(content))

# Let's search for "Bí Mật Cậu Nhỏ" (Vietnamese or escaped)
print("\nSearching for uploader...")
# Escape representation for Bí Mật Cậu Nhỏ:
# B\u00ed M\u1eaet C\u1eadu Nh\u1ecf
escaped_uploader = r"B\\u00ed\s*M\\u1eaet\s*C\\u1eadu\s*Nh\\u1ecf"
uploader_match = re.search(escaped_uploader, content, re.IGNORECASE)
if uploader_match:
    print("Found escaped uploader at position:", uploader_match.start())
    pos = uploader_match.start()
    print("Uploader Context:", content[pos-200:pos+500])
else:
    print("Escaped uploader not found.")
    
# Let's search for the view count "240529"
print("\nSearching for view count 240529...")
pos_view = content.find("240529")
if pos_view != -1:
    print("Found view count at position:", pos_view)
    print("View count context:", content[pos_view-200:pos_view+200])
else:
    print("View count not found.")

# Let's search for the word "reaction" or "feedback" or "like" or "comment" near the view count if found,
# or generally in the file
print("\nSearching for feedback or reaction or like properties...")
feedback_matches = re.findall(r'("\w*(?:like|reaction|feedback|comment|share)\w*"\s*:\s*(?:[^,{}"]+|"[^"]*"))', content, re.IGNORECASE)
print("Total matches:", len(feedback_matches))
print("First 30 matches:")
for m in feedback_matches[:30]:
    print(" ", m)
