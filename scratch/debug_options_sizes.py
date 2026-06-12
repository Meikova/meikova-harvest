import requests
import re
from urllib.parse import urljoin
import urllib3
urllib3.disable_warnings()

url1 = "https://vip.opstream90.com/20260605/33879_0038c2d2/index.m3u8"
url2 = "https://v7.kkphimplayer7.com/20260605/mMUnxegG/index.m3u8"
referer = "https://motchilli.ac/phim/bai-hoc-dang-doi-1780648256/tap-1"

def resolve_hls_size_debug(m3u8_url, referer=None):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if referer:
            headers["Referer"] = referer
            
        print(f"Fetching manifest from: {m3u8_url}")
        resp = requests.get(m3u8_url, headers=headers, verify=False, timeout=5)
        print(f"Manifest status: {resp.status_code}")
        
        content = resp.text
        if "#EXT-X-STREAM-INF" in content:
            # Extract lines that don't start with # and aren't empty
            variants = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
            if variants:
                variant_url = variants[0]
                if not variant_url.startswith("http"):
                    variant_url = urljoin(m3u8_url, variant_url)
                print(f"Redirecting to variant: {variant_url}")
                return resolve_hls_size_debug(variant_url, referer)
                
        segments = []
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                segments.append(line)
                
        print(f"Total segments found: {len(segments)}")
        if not segments:
            return None
            
        total_segments = len(segments)
        mid_idx = total_segments // 2
        target_segment = segments[mid_idx]
        if not target_segment.startswith("http"):
            target_segment = urljoin(m3u8_url, target_segment)
            
        print(f"Target segment: {target_segment}")
        
        seg_resp = requests.head(target_segment, headers=headers, verify=False, timeout=5)
        print(f"HEAD Status: {seg_resp.status_code}")
        
        content_len = seg_resp.headers.get("Content-Length")
        if not content_len:
            seg_resp = requests.get(target_segment, headers=headers, verify=False, stream=True, timeout=5)
            print(f"GET Status: {seg_resp.status_code}")
            content_len = seg_resp.headers.get("Content-Length")
            
        if content_len:
            size_bytes = int(content_len) * total_segments
            print(f"Final calculated size: {size_bytes} bytes (~{size_bytes / (1024*1024):.2f} MB)")
            return size_bytes
    except Exception as e:
        print(f"Exception: {e}")
    return None

print("\n--- Testing URL 1 ---")
resolve_hls_size_debug(url1, referer)
print("\n--- Testing URL 2 ---")
resolve_hls_size_debug(url2, referer)
