import subprocess

url = "https://www.facebook.com/share/p/18KCdDUac7/"

command = [
    "curl",
    "-I",  # Just headers
    "-L",  # Follow redirects
    "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "-H", "Accept-Language: vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    url
]

print("Running curl...")
result = subprocess.run(command, capture_output=True, text=True, errors="ignore")
print(result.stdout)
print(result.stderr)
