import re

with open("scratch/all_fbcdn_urls.txt", "r", encoding="utf-8") as f:
    urls = f.read().splitlines()

candidates = []
for u in urls:
    # Look for scontent video thumbnail paths (typically contains /t15. or /t39. or /t51. or /p)
    if "scontent" in u and ("t15." in u or "t39." in u or "t51." in u or "p50x50" not in u):
        # Filter out profile pictures (which usually have /cp0/ or /p50x50/ or /p100x100/)
        if not any(x in u for x in ["/cp0/", "/p50x50/", "/p100x100/", "/p60x60/"]):
            # Filter out icons
            if "rsrc.php" not in u and ".ico" not in u and ".gif" not in u:
                candidates.append(u)

print(f"Found {len(candidates)} candidate image URLs:")
for idx, c in enumerate(candidates):
    print(f"[{idx}] {c}")
