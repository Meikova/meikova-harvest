import re

filepath = "static/css/styles.css"

with open(filepath, "r", encoding="utf-8") as f:
    css = f.read()

# 1. Replace hardcoded cyan RGB (99, 179, 237) with var(--cyan-rgb)
# We exclude the root definition: --cyan-rgb: 99, 179, 237;
# We can do this by replacing all instances of 'rgba(99, 179, 237,' with 'rgba(var(--cyan-rgb),'
# We also replace any instances of 'rgba(99,179,237,' (without spaces)
css_new = re.sub(r'rgba\(\s*99\s*,\s*179\s*,\s*237\s*,', 'rgba(var(--cyan-rgb),', css)

# 2. Replace hardcoded purple RGB (183, 148, 244) with var(--purple-rgb)
css_new = re.sub(r'rgba\(\s*183\s*,\s*148\s*,\s*244\s*,', 'rgba(var(--purple-rgb),', css_new)

# Let's check how many replacements were made
old_cyan_matches = len(re.findall(r'rgba\(\s*99\s*,\s*179\s*,\s*237\s*,', css))
new_cyan_matches = len(re.findall(r'rgba\(\s*99\s*,\s*179\s*,\s*237\s*,', css_new))
print(f"Cyan replacements: {old_cyan_matches} -> {new_cyan_matches}")

old_purple_matches = len(re.findall(r'rgba\(\s*183\s*,\s*148\s*,\s*244\s*,', css))
new_purple_matches = len(re.findall(r'rgba\(\s*183\s*,\s*148\s*,\s*244\s*,', css_new))
print(f"Purple replacements: {old_purple_matches} -> {new_purple_matches}")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(css_new)
print("Updated static/css/styles.css successfully.")
