import requests
import time
from concurrent.futures import ThreadPoolExecutor
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 24 slide image urls
urls = [
    "https://p16-common-sign.tiktokcdn.com/tos-alisg-i-photomode-sg/0b596b1e4e4042f099cb8b1da8a75fd0~tplv-photomode-image.jpeg?dr=14555&x-expires=1781190000&x-signature=65Oxut7aSUKKHM00V%2B5CW1lBc1o%3D&t=4d5b0474&ps=13740610&shp=81f88b70&shcp=9b759fb9&idc=my2&ftpl=1",
    "https://p16-common-sign.tiktokcdn.com/tos-alisg-i-photomode-sg/33421a8e7fb04ff9b23f92a175803c8b~tplv-photomode-image.jpeg?dr=14555&x-expires=1781190000&x-signature=27ZAw%2FB%2Fq%2BEFiP4WPDgSGC4Sp%2Bo%3D&t=4d5b0474&ps=13740610&shp=81f88b70&shcp=9b759fb9&idc=my2&ftpl=1",
    "https://p16-common-sign.tiktokcdn.com/tos-alisg-i-photomode-sg/ecef94000f504aacaddbc8127d068e01~tplv-photomode-image.jpeg?dr=14555&x-expires=1781190000&x-signature=iU%2FF1r6N4dOQe3R1LqY%2Br%2Bx0Msk%3D&t=4d5b0474&ps=13740610&shp=81f88b70&shcp=9b759fb9&idc=my2&ftpl=1"
] * 8 # duplicate to make 24 urls

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
}

def resolve_size(url):
    try:
        r = requests.head(url, headers=headers, timeout=3)
        if r.status_code == 200:
            return r.headers.get("content-length")
    except Exception:
        pass
    return None

start = time.time()
print("Starting parallel size resolution of 24 URLs...")
with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(resolve_size, urls))
duration = time.time() - start

print(f"Finished in {duration:.2f} seconds")
print(f"Successfully resolved {len([r for r in results if r])} sizes out of 24")
