import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ffmpeg import translate_vtt_file

vtt_content = """WEBVTT
Kind: captions
Language: vi

00:00:02.080 --> 00:00:04.390
Nào, chuẩn bị lao mình xuống biển cả đầy

00:00:04.390 --> 00:00:04.400
Nào, chuẩn bị lao mình xuống biển cả đầy

00:00:04.400 --> 00:00:07.550
Nào, chuẩn bị lao mình xuống biển cả đầy bí ẩn, còn gọi là biển đen nhé. Đây là

00:00:07.550 --> 00:00:07.560
bí ẩn, còn gọi là biển đen nhé. Đây là

00:00:07.560 --> 00:00:10.190
bí ẩn, còn gọi là biển đen nhé. Đây là vùng nước nội địa lớn nhất thế giới, còn

00:00:10.190 --> 00:00:10.200
vùng nước nội địa lớn nhất thế giới, còn

00:00:10.200 --> 00:00:13.749
vùng nước nội địa lớn nhất thế giới, còn rộng hơn cả toàn bang California.
"""

temp_vtt = "scratch/temp_test.vtt"
os.makedirs("scratch", exist_ok=True)
with open(temp_vtt, "w", encoding="utf-8") as f:
    f.write(vtt_content)

print("Translating and deduplicating mock VTT...")
translate_vtt_file(temp_vtt, target_lang="vi")

with open(temp_vtt, "r", encoding="utf-8") as f:
    result = f.read()

print("\n=== RESULTING VTT ===")
print(result)

# Clean up
if os.path.exists(temp_vtt):
    os.remove(temp_vtt)
