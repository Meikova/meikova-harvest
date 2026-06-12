import re

with open("scratch/phimchill.html", "r", encoding="utf-8") as f:
    html = f.read()

scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)

with open("scratch/phimchill_scripts.txt", "w", encoding="utf-8") as f:
    for i, s in enumerate(scripts):
        f.write(f"\n=================== SCRIPT {i} ===================\n")
        f.write(s)
        f.write("\n")

print(f"Extracted {len(scripts)} scripts to scratch/phimchill_scripts.txt")
