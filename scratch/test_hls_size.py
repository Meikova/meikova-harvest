import requests
import re
from urllib.parse import urljoin, urlparse
import urllib3
urllib3.disable_warnings()

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://motchilli.ac/"
}

def estimate_hls_size(m3u8_url):
    try:
        # 1. Fetch manifest
        resp = requests.get(m3u8_url, headers=headers, verify=False, timeout=8)
        if resp.status_code != 200:
            print(f"Failed to fetch manifest: HTTP {resp.status_code} for {m3u8_url}")
            return None
        
        content = resp.text
        
        # 2. Check if it's a master playlist
        if "#EXT-X-STREAM-INF" in content:
            # Find all variant playlists
            variants = re.findall(r'(https?://[^\s#]+|[\w.-]+/\w+\.m3u8|[\w.-]+\.m3u8)', content)
            if variants:
                # Use the first variant (usually highest quality or default)
                variant_url = variants[0]
                if not variant_url.startswith("http"):
                    variant_url = urljoin(m3u8_url, variant_url)
                print(f"Master playlist detected. Redirecting to variant: {variant_url}")
                return estimate_hls_size(variant_url)
            
        # 3. Parse segments
        segments = []
        lines = content.splitlines()
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                segments.append(line)
                
        if not segments:
            print("No segments found in manifest.")
            return None
            
        total_segments = len(segments)
        # Use a middle segment to avoid initial ads/intro clips
        mid_idx = total_segments // 2
        target_segment = segments[mid_idx]
        if not target_segment.startswith("http"):
            target_segment = urljoin(m3u8_url, target_segment)
            
        print(f"Total segments: {total_segments} | Target segment ({mid_idx}): {target_segment}")
        
        # 4. Fetch content-length of the target segment
        seg_resp = requests.head(target_segment, headers=headers, verify=False, timeout=8)
        content_len = seg_resp.headers.get("Content-Length")
        if not content_len:
            # Try GET request with stream=True
            seg_resp = requests.get(target_segment, headers=headers, verify=False, stream=True, timeout=8)
            content_len = seg_resp.headers.get("Content-Length")
            
        if content_len:
            seg_size = int(content_len)
            estimated_total = seg_size * total_segments
            print(f"Target segment size: {seg_size} bytes")
            print(f"Estimated total HLS size: {estimated_total} bytes (~{estimated_total / (1024 * 1024):.2f} MB)")
            return estimated_total
        else:
            print("Could not get Content-Length of the target segment.")
            return None
            
    except Exception as e:
        print(f"Error estimating size: {e}")
        return None

if __name__ == "__main__":
    urls = [
        "https://fcloud.live/player/master/1780659758220_ep135015_episode_135015",
        "https://vip.opstream90.com/20260605/33879_0038c2d2/index.m3u8"
    ]
    for url in urls:
        print(f"\nEstimating size for: {url}")
        estimate_hls_size(url)
        print("-" * 50)
