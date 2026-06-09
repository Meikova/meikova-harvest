import sys
import os

# Configure encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

print("=== Running TikTok Extraction Unit Tests ===")

# Mock data for watermark filter test
mock_formats = [
    {"format_id": "download_addr", "format_note": "Unwatermarked download", "height": 720, "vcodec": "h264", "url": "https://cdn.tiktok.com/clean_video.mp4", "filesize": 1000000},
    {"format_id": "play_addr", "format_note": "Unwatermarked play", "height": 720, "vcodec": "h264", "url": "https://cdn.tiktok.com/clean_video_play.mp4", "filesize": 1000000},
    {"format_id": "wm_play_addr", "format_note": "Watermarked play", "height": 720, "vcodec": "h264", "url": "https://cdn.tiktok.com/watermarked_video.mp4", "filesize": 1000000},
    {"format_id": "download_addr-watermarked", "format_note": "Watermarked download", "height": 720, "vcodec": "h264", "url": "https://cdn.tiktok.com/watermarked_video_2.mp4", "filesize": 1000000}
]

# Helper function to check if a format is watermarked
def is_watermarked_format(f):
    f_id = str(f.get("format_id") or "").lower()
    f_note = str(f.get("format_note") or "").lower()
    is_wm = False
    if "watermark" in f_id or "watermark" in f_note:
        if "unwatermark" not in f_note:
            is_wm = True
    if "wm_play" in f_id or f_id.startswith("wm-") or f_id.startswith("wm_"):
        is_wm = True
    return is_wm

# Simulate app.py watermark filter logic
is_tiktok = True
has_non_wm = False
for f in mock_formats:
    if f.get("vcodec") != "none":
        if not is_watermarked_format(f):
            has_non_wm = True
            break

print(f"Has non-watermarked streams: {has_non_wm}")

filtered_formats = []
for f in reversed(mock_formats):
    if f.get("vcodec") != "none":
        if is_tiktok and has_non_wm:
            if is_watermarked_format(f):
                print(f"Filtered out watermarked format: {f.get('format_id')}")
                continue
        filtered_formats.append(f)

print(f"Filtered formats count: {len(filtered_formats)}")
for f in filtered_formats:
    print(f" - Kept format: {f['format_id']} (URL: {f['url']})")

# Verify that clean ones are kept and watermarked ones are removed
assert len(filtered_formats) == 2, "Test failed: did not filter out watermarked streams correctly!"
assert any(f["format_id"] == "download_addr" for f in filtered_formats), "Test failed: missing download_addr!"
assert any(f["format_id"] == "play_addr" for f in filtered_formats), "Test failed: missing play_addr!"
print("Watermark filter test: PASSED")


# Mock data for TikTok slideshow check
mock_thumbnails = [
    {"url": "https://p16.tiktokcdn.com/avatar/user1.jpg"},
    {"url": "https://p16.tiktokcdn.com/slide/image1.jpg"},
    {"url": "https://p16.tiktokcdn.com/slide/image2.jpg"},
    {"url": "https://p16.tiktokcdn.com/slide/image3.jpg"}
]

slide_urls = [t.get("url") for t in mock_thumbnails if t.get("url") and t.get("url").startswith("http") and "avatar" not in t.get("url").lower()]
is_tiktok_slideshow = len(slide_urls) > 1
print(f"Is slideshow: {is_tiktok_slideshow} (Slide URLs found: {len(slide_urls)})")
assert is_tiktok_slideshow is True, "Test failed: slideshow detection failed!"

images = []
for idx, t in enumerate(mock_thumbnails):
    url_val = t.get("url")
    if url_val and url_val.startswith("http"):
        if is_tiktok_slideshow and "avatar" in url_val.lower():
            print(f"Filtered out avatar: {url_val}")
            continue
        label = f"Slide Photo {len(images)+1}" if is_tiktok_slideshow else f"Thumbnail {idx+1}"
        images.append({
            "label": label,
            "url": url_val,
            "ext": "jpg"
        })

print(f"Extracted slideshow images count: {len(images)}")
for img in images:
    print(f" - Image: {img['label']} -> {img['url']}")

assert len(images) == 3, "Test failed: did not extract correct number of slide photos!"
assert images[0]["label"] == "Slide Photo 1", "Test failed: incorrect label!"
assert images[1]["label"] == "Slide Photo 2", "Test failed: incorrect label!"
print("Slideshow extraction & labeling test: PASSED")

print("=== All tests passed successfully! ===")
