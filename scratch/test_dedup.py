"""Quick test to verify the chain-based dedup against the real VTT data."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

from utils.ffmpeg import parse_time_to_ms
import re

pattern = r"((?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})\s*-->\s*((?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})[^\r\n]*\r?\n(.*?)(?=\r?\n(?:\d{2}:)?\d{2}:\d{2}[.,]\d{3}|\Z)"
matches = list(re.finditer(pattern, vtt_content, re.DOTALL))

print(f"Total raw cues: {len(matches)}")

# Step 1: Filter micro-duration
parsed_cues = []
for idx, m in enumerate(matches):
    start_ms = parse_time_to_ms(m.group(1).replace(",", "."))
    end_ms = parse_time_to_ms(m.group(2).replace(",", "."))
    if end_ms - start_ms <= 50:
        continue
    text = re.sub(r'<[^>]+>', '', m.group(3).strip()).replace('\n', ' ').strip()
    text = re.sub(r'<\d{2}:\d{2}:\d{2}\.\d{3}>', '', text).strip()
    if text:
        parsed_cues.append((idx, m, start_ms, end_ms, text))

print(f"After micro-duration filter: {len(parsed_cues)}")
for i, (idx, m, s, e, t) in enumerate(parsed_cues):
    print(f"  [{i}] {s}ms -> {e}ms | {t[:70]}")

# Step 2: Chain-based dedup
def tail_head_overlap(text_a, text_b, min_match_words=2):
    words_a = text_a.lower().split()
    words_b = text_b.lower().split()
    if len(words_a) < min_match_words or len(words_b) < min_match_words:
        return False
    max_check = min(len(words_a), len(words_b))
    for n in range(min_match_words, max_check + 1):
        if words_a[-n:] == words_b[:n]:
            return True
    return False

def is_rolling_pair(cue_a, cue_b):
    idx_a, m_a, start_a, end_a, text_a = cue_a
    idx_b, m_b, start_b, end_b, text_b = cue_b
    if start_b > end_a + 100:
        return False
    if text_a.lower().strip() in text_b.lower().strip():
        return True
    if tail_head_overlap(text_a, text_b, min_match_words=2):
        return True
    return False

chains = []
current_chain = [parsed_cues[0]] if parsed_cues else []
for i in range(1, len(parsed_cues)):
    if is_rolling_pair(current_chain[-1], parsed_cues[i]):
        current_chain.append(parsed_cues[i])
    else:
        chains.append(current_chain)
        current_chain = [parsed_cues[i]]
if current_chain:
    chains.append(current_chain)

print(f"\nChains found: {len(chains)}")
for ci, chain in enumerate(chains):
    print(f"  Chain {ci}: {len(chain)} cues")
    for idx, m, s, e, t in chain:
        print(f"    {s}ms -> {e}ms | {t[:70]}")

# Build final cues from chains
final_cues = []
for chain in chains:
    first_idx, first_m, first_start, first_end, first_text = chain[0]
    last_idx, last_m, last_start, last_end, last_text = chain[-1]
    final_cues.append((last_idx, last_m, first_start, last_end, last_text))

print(f"\n=== FINAL CUES ({len(final_cues)}) ===")
for idx, m, start_ms, end_ms, text in final_cues:
    print(f"  {start_ms}ms -> {end_ms}ms | {text}")
