import os
import re
import asyncio
import logging
import subprocess
import edge_tts
import urllib.parse
import requests

logger = logging.getLogger(__name__)


def parse_time_to_ms(time_str):
    if not time_str:
        return 0
    time_str = str(time_str).strip()
    parts = time_str.split(':')
    try:
        if len(parts) == 3:
            h, m, s = parts
        elif len(parts) == 2:
            h = 0
            m, s = parts
        else:
            h = 0
            m = 0
            s = parts[0]
            
        if '.' in str(s):
            sec, ms = str(s).split('.')
            ms = ms.ljust(3, '0')[:3]
            ms_val = int(ms)
        elif ',' in str(s):
            sec, ms = str(s).split(',')
            ms = ms.ljust(3, '0')[:3]
            ms_val = int(ms)
        else:
            sec = s
            ms_val = 0
            
        return int(h) * 3600000 + int(m) * 60000 + int(sec) * 1000 + ms_val
    except Exception:
        return 0


def format_ms_to_vtt_time(ms):
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    milliseconds = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d}.{milliseconds:03d}"


def trim_file_if_needed(filepath, trim_start, trim_end):
    """Trims the media file using FFmpeg based on starting and ending timestamps."""
    if not filepath or not os.path.exists(filepath):
        return filepath
    
    start = str(trim_start or "").strip()
    end = str(trim_end or "").strip()
    
    def is_zero_time(t):
        if not t:
            return True
        t_clean = t.replace(":", "").replace(".", "").strip()
        try:
            return int(t_clean) == 0
        except Exception:
            return False
            
    if (not start or is_zero_time(start)) and (not end or is_zero_time(end)):
        return filepath
        
    logger.info(f"Trimming file {filepath} from {start} to {end or 'EOF'}...")
    
    base, ext = os.path.splitext(filepath)
    output_filepath = base + "_trimmed" + ext
    
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except Exception as path_e:
        logger.warning(f"Failed to add static-ffmpeg paths for trimming: {path_e}")
        
    # 1. Try FAST stream copy trimming first (runs in milliseconds, lossless)
    cmd_copy = ["ffmpeg", "-y"]
    if start and not is_zero_time(start):
        cmd_copy.extend(["-ss", start])
    if end and not is_zero_time(end):
        cmd_copy.extend(["-to", end])
    cmd_copy.extend([
        "-i", filepath,
        "-c", "copy",
        "-map", "0:v?", "-map", "0:a?",
        output_filepath
    ])
    
    logger.info(f"Trying fast stream copy trim: {' '.join(cmd_copy)}")
    result = subprocess.run(cmd_copy, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    if result.returncode == 0 and os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 1000:
        logger.info("Fast stream copy trimming successful. Replacing original file.")
        try:
            os.remove(filepath)
            os.rename(output_filepath, filepath)
            return filepath
        except Exception as replace_err:
            logger.warning(f"Failed to replace trimmed file: {replace_err}")
            return output_filepath

    # 2. Fallback to accurate transcoding trim if copy fails (or results in corrupted/empty file)
    logger.warning("Fast stream copy trim failed or was not possible. Falling back to transcoding trim...")
    if os.path.exists(output_filepath):
        try:
            os.remove(output_filepath)
        except Exception:
            pass

    cmd_transcode = ["ffmpeg", "-y"]
    if start and not is_zero_time(start):
        cmd_transcode.extend(["-ss", start])
    if end and not is_zero_time(end):
        cmd_transcode.extend(["-to", end])
        
    cmd_transcode.extend([
        "-i", filepath,
        "-c:v", "libx264", "-preset", "superfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v", "-map", "0:a?",
        output_filepath
    ])
    
    logger.info(f"Running transcode trim: {' '.join(cmd_transcode)}")
    res_trans = subprocess.run(cmd_transcode, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    if res_trans.returncode == 0 and os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 0:
        logger.info("Transcoding trim successful. Replacing original file.")
        try:
            os.remove(filepath)
            os.rename(output_filepath, filepath)
            return filepath
        except Exception as replace_err:
            logger.warning(f"Failed to replace trimmed file: {replace_err}")
            return output_filepath
    else:
        logger.error(f"Transcoding trim fallback failed (code {res_trans.returncode}). Stderr: {res_trans.stderr}")
        if os.path.exists(output_filepath):
            try:
                os.remove(output_filepath)
            except Exception:
                pass
            return filepath


async def generate_voiceover_clip_async(text, voice, output_path, semaphore, rate=None, pitch=None):
    async with semaphore:
        for attempt in range(3):
            try:
                communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
                # Set a 15-second timeout for each clip generation to prevent indefinite hangs
                await asyncio.wait_for(communicate.save(output_path), timeout=15.0)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    return True
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed to synthesize clip: {text[:20]} - Error: {e}")
                await asyncio.sleep(0.5)
        return False



async def run_batch_tts(tasks_list, voiceover_voice, rate=None, pitch=None):
    semaphore = asyncio.Semaphore(15)
    async_tasks = []
    for text, path in tasks_list:
        async_tasks.append(generate_voiceover_clip_async(text, voiceover_voice, path, semaphore, rate=rate, pitch=pitch))
    results = await asyncio.gather(*async_tasks, return_exceptions=True)
    return results


def has_audio_stream(filepath):
    """Checks if the media file has an audio stream using ffprobe."""
    if not filepath or not os.path.exists(filepath):
        return False
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=codec_type",
        "-of", "csv=p=0",
        filepath
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return "audio" in (result.stdout or "").strip().lower()
    except Exception as e:
        logger.warning(f"Error checking audio stream presence: {e}")
        return False


def translate_text(text, target_lang="vi"):
    if not text.strip():
        return ""
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            translated = "".join([part[0] for part in data[0] if part[0]])
            return translated
    except Exception as e:
        logger.warning(f"Translation failed for '{text[:20]}': {e}")
    return text


def translate_cues_batch(cues, target_lang="vi"):
    """
    Translates a list of cue texts in batch to minimize HTTP requests and avoid rate limiting.
    cues: list of (idx, cue_text)
    """
    if not cues:
        return {}
        
    translated_map = {}
    
    # Group cues into chunks of max 4000 characters
    current_chunk = []
    current_length = 0
    chunks = []
    
    for idx, text in cues:
        item_text = f"[{idx}] {text}"
        if current_length + len(item_text) + 1 > 4000:
            chunks.append(current_chunk)
            current_chunk = [(idx, text)]
            current_length = len(item_text)
        else:
            current_chunk.append((idx, text))
            current_length += len(item_text) + 1
            
    if current_chunk:
        chunks.append(current_chunk)
        
    for chunk in chunks:
        payload_lines = [f"[{idx}] {text}" for idx, text in chunk]
        payload = "\n".join(payload_lines)
        
        translated_payload = ""
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={urllib.parse.quote(payload)}"
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                translated_payload = "".join([part[0] for part in data[0] if part[0]])
            else:
                logger.warning(f"Batch translation API error (HTTP {resp.status_code})")
        except Exception as e:
            logger.warning(f"Batch translation request failed: {e}")
            
        if translated_payload:
            lines = translated_payload.splitlines()
            current_idx = None
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                match = re.match(r'^\[(\d+)\](.*)', line)
                if match:
                    current_idx = int(match.group(1))
                    text_val = match.group(2).strip()
                    translated_map[current_idx] = text_val
                elif current_idx is not None:
                    translated_map[current_idx] = (translated_map[current_idx] + " " + line).strip()
        
        # Fallback for any failed cues
        for idx, text in chunk:
            if idx not in translated_map:
                translated_map[idx] = translate_text(text, target_lang)
                
    return translated_map


def split_text_and_time(text, start_ms, end_ms, max_words=10):
    """Splits a long text string into smaller segments of at most max_words,
    distributing the duration proportionally among them."""
    words = text.split()
    if not words:
        return []
    if len(words) <= max_words:
        return [(start_ms, end_ms, text)]
        
    segments = []
    total_words = len(words)
    total_duration = max(100, end_ms - start_ms)
    
    current_word_idx = 0
    while current_word_idx < total_words:
        segment_words = words[current_word_idx : current_word_idx + max_words]
        segment_text = " ".join(segment_words)
        
        seg_start = start_ms + int((current_word_idx / total_words) * total_duration)
        current_word_idx += len(segment_words)
        seg_end = start_ms + int((current_word_idx / total_words) * total_duration)
        
        segments.append((seg_start, seg_end, segment_text))
        
    return segments


def ensure_vtt_format(sub_path):
    """
    Checks if the subtitle is SRT or other format, converts it to clean WebVTT,
    and returns the new VTT file path. If it's already VTT, does nothing.
    """
    if not sub_path or not os.path.exists(sub_path):
        return sub_path
        
    if sub_path.lower().endswith(".vtt"):
        # Let's check if it has WEBVTT header, if not, prepend it
        try:
            with open(sub_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if not content.strip().startswith("WEBVTT"):
                with open(sub_path, 'w', encoding='utf-8') as f:
                    f.write("WEBVTT\n\n" + content)
        except Exception as e:
            logger.warning(f"Error checking VTT header: {e}")
        return sub_path
        
    # If it is SRT, convert to VTT
    if sub_path.lower().endswith(".srt"):
        try:
            with open(sub_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            vtt_lines = ["WEBVTT\n\n"]
            for line in lines:
                line_stripped = line.strip()
                # Skip numeric cue numbers
                if line_stripped.isdigit():
                    continue
                # Replace comma with dot in timestamps line
                if "-->" in line:
                    line = line.replace(",", ".")
                vtt_lines.append(line)
                
            vtt_path = sub_path.rsplit(".", 1)[0] + ".vtt"
            with open(vtt_path, 'w', encoding='utf-8') as f:
                f.writelines(vtt_lines)
                
            # Remove original srt file
            try:
                os.remove(sub_path)
            except Exception:
                pass
            return vtt_path
        except Exception as e:
            logger.error(f"Failed to convert SRT to VTT: {e}")
            
    return sub_path


def translate_vtt_file(vtt_path, target_lang="vi", trim_start=None, trim_end=None):
    """Reads a VTT file, translates all caption cues in batch, aggressively deduplicates
    YouTube rolling captions, filters and shifts according to trim range, and overwrites the file."""
    if not vtt_path or not os.path.exists(vtt_path):
        return
    try:
        with open(vtt_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        pattern = r"((?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})\s*-->\s*((?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})[^\r\n]*\r?\n(.*?)(?=\r?\n(?:\d{2}:)?\d{2}:\d{2}[.,]\d{3}|\Z)"
        matches = list(re.finditer(pattern, content, re.DOTALL))
        
        if not matches:
            logger.warning("No subtitle cues found to translate.")
            return

        trim_start_ms = parse_time_to_ms(trim_start) if trim_start else 0
        trim_end_ms = parse_time_to_ms(trim_end) if trim_end else None

        # Step 1: Parse all cues within the trim range, skip micro-duration gap fillers (≤50ms)
        parsed_cues = []
        for idx, m in enumerate(matches):
            start_str = m.group(1).replace(",", ".")
            end_str = m.group(2).replace(",", ".")
            start_ms = parse_time_to_ms(start_str)
            end_ms = parse_time_to_ms(end_str)
            
            # Filter by trim range
            if trim_start_ms > 0 or trim_end_ms is not None:
                if end_ms <= trim_start_ms:
                    continue
                if trim_end_ms is not None and start_ms >= trim_end_ms:
                    continue
            
            # Skip micro-duration gap filler cues (YouTube inserts 10ms cues as transitions)
            duration_ms = end_ms - start_ms
            if duration_ms <= 50:
                continue
            
            text = m.group(3).strip()
            clean_text = re.sub(r'<[^>]+>', '', text).replace('\n', ' ').strip()
            # Also strip inline timestamp tags like <00:00:01.234>
            clean_text = re.sub(r'<\d{2}:\d{2}:\d{2}\.\d{3}>', '', clean_text).strip()
            if clean_text:
                parsed_cues.append((idx, m, start_ms, end_ms, clean_text))

        logger.info(f"After trim & micro-duration filter: {len(parsed_cues)} cues remain")

        # Step 2: Group rolling captions into chains, keep only the final (most complete) cue per chain.
        # YouTube rolling captions: each new cue drops words from the front and appends new words at the back.
        # We detect chains by checking if consecutive cues are linked by:
        #   (a) substring containment, or
        #   (b) tail-head word sequence overlap
        # For each chain, we output a single cue with the START time of the first cue
        # and the TEXT of the last cue (most complete).
        
        def tail_head_overlap(text_a, text_b, min_match_words=2):
            """Check if the tail words of text_a match the head words of text_b."""
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
            """Check if cue_b is a rolling continuation of cue_a."""
            idx_a, m_a, start_a, end_a, text_a = cue_a
            idx_b, m_b, start_b, end_b, text_b = cue_b
            # Must be near-adjacent (gap ≤ 100ms)
            if start_b > end_a + 100:
                return False
            # Substring: text_a fully inside text_b
            if text_a.lower().strip() in text_b.lower().strip():
                return True
            # Tail-head: tail of text_a == head of text_b
            if tail_head_overlap(text_a, text_b, min_match_words=2):
                return True
            return False

        # Build chains
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

        # For each chain: take start_ms from first cue, end_ms from last cue, and merge their texts to construct complete sentences
        final_cues = []
        for chain in chains:
            first_idx, _, first_start, _, _ = chain[0]
            _, last_m, _, last_end, _ = chain[-1]
            
            # Reconstruct the full sentence by joining non-overlapping words in sequence
            texts = [c[4] for c in chain]
            merged_text = texts[0]
            for next_text in texts[1:]:
                words_merged = merged_text.split()
                words_next = next_text.split()
                
                max_overlap = 0
                limit = min(len(words_merged), len(words_next))
                for n in range(1, limit + 1):
                    # Robust comparison stripping punctuation and ignoring case
                    suffix = [w.lower().strip(".,?!;:-") for w in words_merged[-n:]]
                    prefix = [w.lower().strip(".,?!;:-") for w in words_next[:n]]
                    if suffix == prefix:
                        max_overlap = n
                        
                new_words = words_next[max_overlap:]
                if new_words:
                    merged_text += " " + " ".join(new_words)
            
            # Clean up excessive spacing
            merged_text = re.sub(r'\s+', ' ', merged_text).strip()
            final_cues.append((first_idx, last_m, first_start, last_end, merged_text))


        logger.info(f"Collapsed {len(parsed_cues)} cues into {len(final_cues)} chains (removed {len(parsed_cues) - len(final_cues)} rolling duplicates)")

        # Step 4: Batch translate the deduplicated cues
        cues_to_translate = [(idx, text) for idx, m, start_ms, end_ms, text in final_cues]
        if target_lang and target_lang != "none":
            translated_map = translate_cues_batch(cues_to_translate, target_lang)
        else:
            translated_map = {idx: text for idx, text in cues_to_translate}

        # Step 5: Reconstruct WebVTT file with shifted, translated, deduplicated, and split cues
        new_lines = ["WEBVTT", "Kind: captions", f"Language: {target_lang or 'original'}", ""]
        for idx, m, start_ms, end_ms, text in final_cues:
            translation = translated_map.get(idx, text)
            
            shifted_start = max(0, start_ms - trim_start_ms)
            shifted_end = max(0, end_ms - trim_start_ms)
            
            # Segment long sentences/chains to prevent giant paragraphs covering the screen
            splitted = split_text_and_time(translation, shifted_start, shifted_end, max_words=10)
            for seg_start, seg_end, seg_text in splitted:
                start_vtt = format_ms_to_vtt_time(seg_start)
                end_vtt = format_ms_to_vtt_time(seg_end)
                new_lines.append(f"{start_vtt} --> {end_vtt}")
                new_lines.append(seg_text)
                new_lines.append("")

        with open(vtt_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(new_lines))
        logger.info(f"Subtitles file {vtt_path} successfully translated, trimmed, and shifted to {target_lang}. Final: {len(final_cues)} cues.")
    except Exception as e:
        logger.error(f"Failed to translate VTT file {vtt_path}: {e}")


def get_audio_duration_ms(filepath):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        filepath
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            return int(float(res.stdout.strip()) * 1000)
    except Exception as e:
        logger.warning(f"Failed to get audio duration for {filepath}: {e}")
        
    try:
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            # Fallback estimation for 24kHz mono MP3 (approx 40kbps, i.e., 5 bytes/ms)
            return max(500, int(size / 5))
    except Exception:
        pass
    return 2000


def get_video_duration_ms(filepath):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        filepath
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            return int(float(res.stdout.strip()) * 1000)
    except Exception as e:
        logger.warning(f"Failed to get video duration for {filepath}: {e}")
    return 0


def overlay_voiceover_tts(filepath, subtitles_path, voiceover_voice, temp_dir, trim_start=None, trim_end=None, progress_callback=None, voiceover_rate=None, voiceover_pitch=None):
    """Synthesizes speech for each subtitle line using edge-tts, schedules them sequentially,
    mixes them in Python to avoid too many inputs, and overlays it onto the video."""
    logger.info(f"Generating AI Voiceover using voice '{voiceover_voice}' (rate={voiceover_rate}, pitch={voiceover_pitch}) from subtitles: {subtitles_path}")
    
    try:
        with open(subtitles_path, 'r', encoding='utf-8') as f:
            vtt_content = f.read()
    except Exception as e:
        logger.error(f"Failed to read subtitles file: {e}")
        return filepath

    # Parse WebVTT cues (robust to optional hours and trailing settings)
    pattern = r"((?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})\s*-->\s*((?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})[^\r\n]*\r?\n(.*?)(?=\r?\n(?:\d{2}:)?\d{2}:\d{2}[.,]\d{3}|\Z)"
    matches = list(re.finditer(pattern, vtt_content, re.DOTALL))
    
    if not matches:
        logger.warning("No subtitle cues found to translate and dub.")
        return filepath

    tasks_list = []
    clips_info = [] # list of (original_start_ms, clip_path)
    
    for idx, m in enumerate(matches):
        start_str = m.group(1).replace(",", ".")
        text = m.group(3).strip()
        text = re.sub(r'<[^>]+>', '', text)  # remove HTML formatting
        text = text.replace('\n', ' ')
        
        if not text:
            continue
            
        start_ms = parse_time_to_ms(start_str)
        
        clip_path = os.path.join(temp_dir, f"tts_clip_{idx}.mp3")
        tasks_list.append((text, clip_path))
        clips_info.append((start_ms, clip_path))

    if not tasks_list:
        logger.warning("No voice clips were synthesized.")
        return filepath

    if progress_callback:
        progress_callback("Synthesizing AI Dubbing voices (parallelized)...", 97)

    logger.info(f"Synthesizing {len(tasks_list)} subtitle cues in parallel...")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(run_batch_tts(tasks_list, voiceover_voice, rate=voiceover_rate, pitch=voiceover_pitch))
        loop.close()
    except Exception as batch_err:
        logger.error(f"Error during parallel TTS generation: {batch_err}")
        results = [False] * len(tasks_list)

    # Filter only successfully generated clips
    clips = []
    for (start_ms, path), success in zip(clips_info, results):
        if success is True and os.path.exists(path) and os.path.getsize(path) > 0:
            clips.append((start_ms, path))
        else:
            # Clean up if it was somehow created but failed
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

    if not clips:
        logger.warning("No voice clips were successfully synthesized.")
        return filepath

    # Sort clips by their original start time
    clips.sort(key=lambda x: x[0])

    # Schedule clips sequentially to prevent overlaps (voices stacked on top of each other)
    scheduled_clips = []
    last_end_time = 0
    for start_ms, path in clips:
        duration_ms = get_audio_duration_ms(path)
        # Ensure each clip starts at or after the previous clip ended + a small natural gap (150ms)
        actual_start_ms = max(start_ms, last_end_time + 150)
        scheduled_clips.append((actual_start_ms, duration_ms, path))
        last_end_time = actual_start_ms + duration_ms

    has_audio = has_audio_stream(filepath)
    video_duration_ms = get_video_duration_ms(filepath)
    voiceover_track_path = os.path.join(temp_dir, "voiceover_mixed.wav")
    
    logger.info("Building single composite voiceover audio track via PCM mixing...")
    
    bytes_per_ms = 48 # 24000Hz * 1 channel * 2 bytes/sample / 1000ms
    max_clip_end = max([start + dur for start, dur, _ in scheduled_clips]) if scheduled_clips else 0
    total_duration_ms = max(video_duration_ms, max_clip_end) + 2000
    
    buffer_size = total_duration_ms * bytes_per_ms
    audio_buffer = bytearray(buffer_size)
    
    for start_ms, duration_ms, mp3_path in scheduled_clips:
        pcm_path = mp3_path + ".raw"
        decode_cmd = [
            "ffmpeg", "-y", "-i", mp3_path,
            "-f", "s16le", "-ac", "1", "-ar", "24000",
            pcm_path
        ]
        subprocess.run(decode_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(pcm_path):
            with open(pcm_path, "rb") as f:
                pcm_data = f.read()
            
            try:
                os.remove(pcm_path)
            except Exception:
                pass
                
            offset = start_ms * bytes_per_ms
            num_samples = len(pcm_data) // 2
            
            for i in range(num_samples):
                buf_idx = offset + i * 2
                if buf_idx + 1 >= len(audio_buffer):
                    break
                
                # Mix the samples and clamp to prevent overflow/clipping
                existing_sample = int.from_bytes(audio_buffer[buf_idx:buf_idx+2], byteorder='little', signed=True)
                new_sample = int.from_bytes(pcm_data[i*2:i*2+2], byteorder='little', signed=True)
                
                mixed = existing_sample + new_sample
                if mixed > 32767:
                    mixed = 32767
                elif mixed < -32768:
                    mixed = -32768
                    
                audio_buffer[buf_idx:buf_idx+2] = mixed.to_bytes(2, byteorder='little', signed=True)
                
    # Write mixed PCM buffer to a raw file
    raw_mixed_path = os.path.join(temp_dir, "voiceover_mixed.raw")
    with open(raw_mixed_path, "wb") as f:
        f.write(audio_buffer)
        
    # Convert raw PCM to standard WAV
    convert_cmd = [
        "ffmpeg", "-y",
        "-f", "s16le", "-ar", "24000", "-ac", "1",
        "-i", raw_mixed_path,
        voiceover_track_path
    ]
    subprocess.run(convert_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    try:
        os.remove(raw_mixed_path)
    except Exception:
        pass

    logger.info(f"Mixing single voiceover track with video (has_audio={has_audio})...")
    if progress_callback:
        progress_callback("Mixing voiceover tracks with video...", 97)
        
    base, ext = os.path.splitext(filepath)
    output_filepath = base + "_dubbed" + ext
    
    # Mix the single voiceover track with the video
    cmd = ["ffmpeg", "-y", "-i", filepath, "-i", voiceover_track_path]
    
    if has_audio:
        filter_complex = "[0:a]volume=0.08[bg];[1:a]volume=1.5[voice];[bg][voice]amix=inputs=2:duration=first[out]"
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[out]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            output_filepath
        ])
    else:
        filter_complex = "[1:a]volume=1.5[voice]"
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[voice]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_filepath
        ])
        
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    
    # Clean up tts mp3 clip files
    for _, path in clips:
        try:
            os.remove(path)
        except Exception:
            pass
            
    # Clean up mixed voiceover track wav file
    if os.path.exists(voiceover_track_path):
        try:
            os.remove(voiceover_track_path)
        except Exception:
            pass
            
    if res.returncode == 0 and os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 0:
        os.remove(filepath)
        os.rename(output_filepath, filepath)
        return filepath
    else:
        logger.error(f"Voiceover mixing failed (code {res.returncode}). Stderr: {res.stderr}")
        if os.path.exists(output_filepath):
            os.remove(output_filepath)
        return filepath


def apply_cinematic_filter(filepath, color_filter):
    """Applies FFmpeg filters for cinematic presets."""
    logger.info(f"Applying cinematic color filter '{color_filter}' to {filepath}...")
    base, ext = os.path.splitext(filepath)
    output_filepath = base + "_filtered" + ext
    
    filter_args = ""
    if color_filter == "cyberpunk":
        filter_args = "eq=saturation=1.5:contrast=1.1,colorbalance=rs=0.1:bs=0.2"
    elif color_filter == "vintage":
        filter_args = "colorchannelmixer=.393:.769:.189:.349:.686:.168:.272:.534:.131,eq=contrast=0.95"
    elif color_filter == "noir":
        filter_args = "format=yuv420p,eq=saturation=0:contrast=1.35:brightness=-0.03"
    elif color_filter == "enhance":
        filter_args = "unsharp=3:3:0.8:3:3:0.8"
        
    if not filter_args:
        return filepath
        
    cmd = ["ffmpeg", "-y", "-i", filepath, "-vf", filter_args, "-c:a", "copy", "-map", "0:v", "-map", "0:a?", output_filepath]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 0:
        os.remove(filepath)
        os.rename(output_filepath, filepath)
        return filepath
    else:
        logger.error(f"Cinematic filter failed (code {res.returncode}). Stderr: {res.stderr}")
        if os.path.exists(output_filepath):
            os.remove(output_filepath)
        return filepath


def apply_video_enhancements(filepath, enhance_beautify=False, enhance_sharpen=0, enhance_upscale="none"):
    """Applies FFmpeg filters for video enhancements (sharpen, beautify, resolution upscaling)."""
    if not enhance_beautify and not enhance_sharpen and (not enhance_upscale or enhance_upscale == "none"):
        return filepath

    logger.info(f"Applying video enhancements to {filepath} (beautify: {enhance_beautify}, sharpen: {enhance_sharpen}, upscale: {enhance_upscale})...")
    base, ext = os.path.splitext(filepath)
    output_filepath = base + "_enhanced" + ext

    # Initialize FFmpeg static-ffmpeg paths if available
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except Exception as path_e:
        logger.warning(f"Failed to add static-ffmpeg paths: {path_e}")

    filter_list = []

    # 1. Auto-Beautify (eq filter for brightness, contrast, saturation)
    if enhance_beautify:
        filter_list.append("eq=contrast=1.05:saturation=1.12:brightness=0.01")

    # 2. Sharpen (unsharp filter)
    # Map sharpen_amount (0-100) to luma_amount (0.0 to 1.5)
    if enhance_sharpen > 0:
        amount = (float(enhance_sharpen) / 100.0) * 1.5
        # Apply sharpen filter only to luma channel to prevent chroma/color noise
        filter_list.append(f"unsharp=luma_msiz_x=5:luma_msiz_y=5:luma_amount={amount:.2f}:chroma_amount=0.0")

    # 3. Resolution Upscale (scale filter with Lanczos)
    if enhance_upscale and enhance_upscale != "none":
        if enhance_upscale == "1080p":
            filter_list.append("scale=-2:1080:flags=lanczos")
        elif enhance_upscale == "1440p":
            filter_list.append("scale=-2:1440:flags=lanczos")
        elif enhance_upscale == "2160p":
            filter_list.append("scale=-2:2160:flags=lanczos")
        elif enhance_upscale == "2x":
            filter_list.append("scale=2*iw:-2:flags=lanczos")

    if not filter_list:
        return filepath

    filter_args = ",".join(filter_list)
    cmd = ["ffmpeg", "-y", "-i", filepath, "-vf", filter_args, "-c:a", "copy", "-map", "0:v", "-map", "0:a?", output_filepath]

    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    if res.returncode == 0 and os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 0:
        try:
            os.remove(filepath)
            os.rename(output_filepath, filepath)
            return filepath
        except Exception as file_err:
            logger.error(f"Failed to replace original file with enhanced version: {file_err}")
            return output_filepath
    else:
        logger.error(f"Video enhancement failed (code {res.returncode}). Stderr: {res.stderr}")
        if os.path.exists(output_filepath):
            try:
                os.remove(output_filepath)
            except Exception:
                pass
        return filepath


def convert_to_gif(filepath):
    """Converts the video file to a looping high-quality GIF."""
    logger.info(f"Converting {filepath} to high-quality GIF...")
    base, _ = os.path.splitext(filepath)
    output_filepath = base + ".gif"
    
    filter_complex = "fps=15,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
    cmd = ["ffmpeg", "-y", "-i", filepath, "-vf", filter_complex, output_filepath]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 0:
        os.remove(filepath)
        return output_filepath
    else:
        logger.error(f"GIF conversion failed (code {res.returncode}). Stderr: {res.stderr}")
        if os.path.exists(output_filepath):
            os.remove(output_filepath)
        return filepath


def convert_to_shorts(filepath):
    """Converts a standard horizontal video to a vertical 9:16 Shorts video using blurred padding."""
    logger.info(f"Converting {filepath} to vertical 9:16 Shorts format...")
    base, ext = os.path.splitext(filepath)
    output_filepath = base + "_shorts" + ext
    
    # Force setsar=1, setsar=1 on overlay output, and setdar=9/16 to prevent display aspect ratio stretching
    filter_complex = "[0:v]scale=180:320,boxblur=5:5,scale=1080:1920,setsar=1[bg];[0:v]scale=1080:-2,setsar=1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,setdar=9/16[outv]"
    cmd = [
        "ffmpeg", "-y", "-i", filepath, 
        "-filter_complex", filter_complex, 
        "-map", "[outv]",
        "-map", "0:a?",
        "-aspect", "9:16",
        "-c:v", "libx264", "-preset", "superfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k", 
        "-shortest", 
        output_filepath
    ]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 0:
        os.remove(filepath)
        os.rename(output_filepath, filepath)
        return filepath
    else:
        logger.error(f"Shorts format conversion failed (code {res.returncode}). Stderr: {res.stderr}")
        if os.path.exists(output_filepath):
            os.remove(output_filepath)
        return filepath


def convert_vtt_to_srt(vtt_path, srt_path):
    """Converts a WebVTT subtitle file to SubRip (SRT) format."""
    try:
        with open(vtt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        out_lines = []
        
        # Skip WEBVTT header and any metadata
        start_idx = 0
        for i, line in enumerate(lines):
            if line.strip() == "WEBVTT" or line.startswith("Kind:") or line.startswith("Language:"):
                continue
            if line.strip() == "" and i == 0:
                continue
            start_idx = i
            break
            
        content = "".join(lines[start_idx:])
        blocks = content.strip().split("\n\n")
        
        counter = 1
        for block in blocks:
            block_lines = block.strip().split("\n")
            if not block_lines or block_lines[0] == "":
                continue
                
            if "-->" in block_lines[0]:
                time_line = block_lines[0]
                text_lines = block_lines[1:]
            elif len(block_lines) > 1 and "-->" in block_lines[1]:
                time_line = block_lines[1]
                text_lines = block_lines[2:]
            else:
                continue
                
            times = time_line.split("-->")
            if len(times) != 2:
                continue
                
            start_t = times[0].strip().replace('.', ',')
            end_t = times[1].strip().replace('.', ',')
            
            def format_srt_time(t):
                parts = t.split(':')
                if len(parts) == 2:
                    t = "00:" + t
                elif len(parts) == 3:
                    h, m, s_ms = parts
                    h = h.zfill(2)
                    m = m.zfill(2)
                    t = f"{h}:{m}:{s_ms}"
                return t
                
            start_t = format_srt_time(start_t)
            end_t = format_srt_time(end_t)
            
            out_lines.append(str(counter))
            out_lines.append(f"{start_t} --> {end_t}")
            for t_line in text_lines:
                out_lines.append(t_line)
            out_lines.append("")
            counter += 1
            
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(out_lines))
        return True
    except Exception as e:
        logger.error(f"Error converting VTT to SRT: {e}")
        return False


def hardsub_video(video_path, subtitles_path, font_name="Arial", font_size=1.4, color="#ffffff", bg_color="#000000", bg_opacity=50, outline=2, outline_color="#000000", position="bottom"):
    """Burns VTT/SRT subtitles directly onto the video frames (hardsub) using relative paths and CWD to avoid Windows drive letter colon issues, applying custom styles."""
    if not video_path or not subtitles_path or not os.path.exists(video_path) or not os.path.exists(subtitles_path):
        return video_path
        
    base, ext = os.path.splitext(video_path)
    if ext.lower() not in [".mp4", ".mkv", ".mov"]:
        return video_path
        
    logger.info(f"Preparing hardsub process for subtitles {subtitles_path} into {video_path}...")
    
    # 1. Identify directories and filenames
    video_dir = os.path.dirname(os.path.abspath(video_path))
    video_name = os.path.basename(video_path)
    
    temp_srt_name = "temp_hardsub.srt"
    temp_srt_path = os.path.join(video_dir, temp_srt_name)
    
    # 2. Convert or copy subtitles to temp_hardsub.srt in the video's directory
    if subtitles_path.lower().endswith(".srt"):
        try:
            import shutil
            shutil.copy2(subtitles_path, temp_srt_path)
        except Exception as e:
            logger.error(f"Failed to copy SRT subtitle to temp directory: {e}")
            return video_path
    else:
        # Convert VTT to SRT
        success = convert_vtt_to_srt(subtitles_path, temp_srt_path)
        if not success or not os.path.exists(temp_srt_path):
            logger.error("Failed to prepare SRT file for hardsub.")
            return video_path

    # Helper to convert HTML hex color + opacity to ASS ABGR color format (&HAABBGGRR)
    def to_ass_color(hex_val, opacity_val=100):
        hex_val = hex_val.strip().lstrip('#')
        if len(hex_val) == 3:
            hex_val = "".join([c*2 for c in hex_val])
        if len(hex_val) != 6:
            hex_val = "ffffff"
        r = hex_val[0:2]
        g = hex_val[2:4]
        b = hex_val[4:6]
        # ASS opacity: 00 is fully opaque, FF is fully transparent
        alpha = int((100 - opacity_val) * 2.55)
        alpha = max(0, min(255, alpha))
        return f"&H{alpha:02X}{b}{g}{r}"

    # Calculate styling parameters
    primary_color = to_ass_color(color, 100)
    outline_color_ass = to_ass_color(outline_color, 100)
    back_color = to_ass_color(bg_color, bg_opacity)
    
    border_style = 3 if bg_opacity > 0 else 1
    fontsize_px = max(10, min(100, int(font_size * 18)))
    alignment = 6 if position == "top" else 2
    outline_val = outline
    shadow_val = 0 if bg_opacity > 0 else 1
    
    force_style = (
        f"Fontname={font_name},"
        f"Fontsize={fontsize_px},"
        f"PrimaryColour={primary_color},"
        f"OutlineColour={outline_color_ass},"
        f"BackColour={back_color},"
        f"BorderStyle={border_style},"
        f"Outline={outline_val},"
        f"Shadow={shadow_val},"
        f"Alignment={alignment},"
        f"MarginV=18"
    )

    # 3. Define output path in video_dir
    output_name = os.path.splitext(video_name)[0] + "_hardsubbed" + ext
    output_path = os.path.join(video_dir, output_name)
    
    logger.info(f"Burning subtitles in local directory: {video_dir} with style: {force_style}")
    
    # We use simple filenames relative to video_dir
    cmd = [
        "ffmpeg", "-y",
        "-i", video_name,
        "-vf", f"subtitles='{temp_srt_name}':force_style='{force_style}'",
        "-c:v", "libx264", "-preset", "superfast", "-crf", "23",
        "-c:a", "copy",
        output_name
    ]
    
    # Run FFmpeg in the context of the video directory
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=video_dir)
    
    # Clean up the temporary srt file immediately
    if os.path.exists(temp_srt_path):
        try:
            os.remove(temp_srt_path)
        except Exception as e:
            logger.warning(f"Failed to remove temp srt file {temp_srt_path}: {e}")
            
    if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        try:
            os.remove(video_path)
            os.rename(output_path, video_path)
            logger.info("Subtitles successfully burned into video.")
            return video_path
        except Exception as err:
            logger.warning(f"Failed to replace video with hardsubbed video: {err}")
            return output_path
    else:
        logger.error(f"Failed to burn subtitles (code {res.returncode}). Stderr: {res.stderr}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return video_path



def softsub_video(video_path, subtitles_path, lang_code="eng"):
    """Muxes subtitles directly into the video stream as a soft subtitle track (no re-encoding)."""
    if not video_path or not subtitles_path or not os.path.exists(video_path) or not os.path.exists(subtitles_path):
        return video_path
        
    base, ext = os.path.splitext(video_path)
    if ext.lower() not in [".mp4", ".mkv", ".mov", ".webm"]:
        return video_path
        
    logger.info(f"Muxing soft subtitles from {subtitles_path} into {video_path}...")
    output_path = base + "_softsubbed" + ext
    
    # Choose subtitle codec based on extension
    sub_codec = "mov_text"
    if ext.lower() == ".mkv":
        sub_codec = "srt"
    elif ext.lower() == ".webm":
        sub_codec = "webvtt"
        
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", subtitles_path,
        "-map", "0:v?",
        "-map", "0:a?",
        "-map", "1",
        "-c", "copy",
        "-c:s", sub_codec,
        "-metadata:s:s:0", f"language={lang_code}",
        "-metadata:s:s:0", "title=Subtitles",
        "-disposition:s:s:0", "default",
        output_path
    ]
    
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        try:
            os.remove(video_path)
            os.rename(output_path, video_path)
            logger.info("Soft subtitles successfully muxed.")
            return video_path
        except Exception as err:
            logger.warning(f"Failed to replace video with softsubbed video: {err}")
            return output_path
    else:
        logger.error(f"Failed to mux soft subtitles (code {res.returncode}). Stderr: {res.stderr}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return video_path


def apply_post_processing(filepath, temp_dir, trim_start=None, trim_end=None, export_type="default", color_filter="none", voiceover_active=False, voiceover_voice="vi-VN-HoaiMyNeural", subtitles_path=None, translate_subs=None, subtitle_lang=None, subtitle_mode="none", subtitle_translate="none", progress_callback=None, voiceover_rate=None, voiceover_pitch=None, audio_eq_bass=0, audio_eq_lowmid=0, audio_eq_highmid=0, audio_eq_treble=0, audio_speed=1.0, audio_voice_preset="normal", sub_font="Arial", sub_size=1.4, sub_color="#ffffff", sub_bg_color="#000000", sub_bg_opacity=50, sub_outline=2, sub_outline_color="#000000", sub_pos="bottom", enhance_beautify=False, enhance_sharpen=0, enhance_upscale="none"):
    """Applies all advanced filters, trimming, voiceovers, and formatting options to the downloaded media file."""
    if not filepath or not os.path.exists(filepath):
        return filepath

    # 1. Trimming if requested
    if trim_start or trim_end:
        if progress_callback:
            progress_callback("Trimming video duration...", 96)
        try:
            filepath = trim_file_if_needed(filepath, trim_start, trim_end)
        except Exception as e:
            logger.error(f"Error during post-process trimming: {e}")

    # 1.5. Translate, trim, and shift subtitles
    target_lang = "none"
    if subtitles_path and os.path.exists(subtitles_path):
        subtitles_path = ensure_vtt_format(subtitles_path)
        if subtitle_translate and subtitle_translate != "none":
            target_lang = subtitle_translate
        elif voiceover_active or (translate_subs == "vi"):
            target_lang = "vi"

        # We always process the subtitle file to clean HTML/XML tags, format timestamps,
        # collapse rolling duplicate captions, and perform translation/trimming.
        if progress_callback:
            progress_callback("Processing subtitles...", 97)
        try:
            translate_vtt_file(subtitles_path, target_lang=target_lang, trim_start=trim_start, trim_end=trim_end)
        except Exception as e:
            logger.error(f"Error processing subtitles VTT: {e}")

    # 2. AI Voiceover Dubbing
    if voiceover_active and subtitles_path and os.path.exists(subtitles_path):
        try:
            filepath = overlay_voiceover_tts(filepath, subtitles_path, voiceover_voice, temp_dir, trim_start=trim_start, trim_end=trim_end, progress_callback=progress_callback, voiceover_rate=voiceover_rate, voiceover_pitch=voiceover_pitch)
        except Exception as e:
            logger.error(f"Error during AI Dubbing: {e}")

    # 3. Cinematic Color Filters
    if color_filter and color_filter != "none":
        if progress_callback:
            progress_callback(f"Applying cinematic filter ({color_filter})...", 98)
        try:
            filepath = apply_cinematic_filter(filepath, color_filter)
        except Exception as e:
            logger.error(f"Error during color filtering: {e}")

    # 3.5. Video Enhancements (Beautify, Sharpen, Resolution Upscale)
    if enhance_beautify or (enhance_sharpen and enhance_sharpen > 0) or (enhance_upscale and enhance_upscale != "none"):
        if progress_callback:
            progress_callback("Applying video enhancements...", 98)
        try:
            filepath = apply_video_enhancements(
                filepath,
                enhance_beautify=enhance_beautify,
                enhance_sharpen=enhance_sharpen,
                enhance_upscale=enhance_upscale
            )
        except Exception as e:
            logger.error(f"Error during video enhancement: {e}")

    # 4. Export type conversions
    if export_type == "gif":
        if progress_callback:
            progress_callback("Converting to GIF...", 99)
        try:
            filepath = convert_to_gif(filepath)
        except Exception as e:
            logger.error(f"Error converting to GIF: {e}")
    elif export_type == "shorts":
        if progress_callback:
            progress_callback("Converting to vertical Shorts...", 99)
        try:
            filepath = convert_to_shorts(filepath)
        except Exception as e:
            logger.error(f"Error converting to vertical Shorts: {e}")

    # 5. Mux/Burn subtitles if requested
    if subtitles_path and os.path.exists(subtitles_path) and export_type != "gif":
        mode = subtitle_mode
        if mode == "none" and translate_subs == "vi":
            mode = "hard"

        if mode == "hard":
            if progress_callback:
                progress_callback("Burning subtitles into video...", 99)
            try:
                filepath = hardsub_video(
                    filepath, subtitles_path,
                    font_name=sub_font,
                    font_size=sub_size,
                    color=sub_color,
                    bg_color=sub_bg_color,
                    bg_opacity=sub_bg_opacity,
                    outline=sub_outline,
                    outline_color=sub_outline_color,
                    position=sub_pos
                )
            except Exception as e:
                logger.error(f"Error burning subtitles: {e}")
        elif mode == "soft":
            if progress_callback:
                progress_callback("Muxing soft subtitles...", 99)
            try:
                sub_lang_code = target_lang if (target_lang and target_lang != "none") else (subtitle_lang or "eng")
                filepath = softsub_video(filepath, subtitles_path, lang_code=sub_lang_code)
            except Exception as e:
                logger.error(f"Error muxing soft subtitles: {e}")

    # 5.5. Apply Audio Effects (EQ, playback speed, and voice FX presets)
    if export_type != "gif":
        try:
            has_eq = any(float(x) != 0 for x in [audio_eq_bass, audio_eq_lowmid, audio_eq_highmid, audio_eq_treble] if x is not None)
        except:
            has_eq = False
        
        has_speed = (audio_speed is not None and float(audio_speed) != 1.0)
        has_voice = (audio_voice_preset and audio_voice_preset != "normal")

        if has_eq or has_speed or has_voice:
            if progress_callback:
                progress_callback("Applying EQ & audio effects...", 98)
            try:
                filepath = apply_audio_effects(
                    filepath,
                    eq_bass=audio_eq_bass,
                    eq_lowmid=audio_eq_lowmid,
                    eq_highmid=audio_eq_highmid,
                    eq_treble=audio_eq_treble,
                    speed=audio_speed,
                    voice_preset=audio_voice_preset
                )
            except Exception as ae_err:
                logger.error(f"Error applying audio effects: {ae_err}")

    return filepath


def has_audio_stream(filepath):
    """Checks if the media file has an audio stream using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0", filepath
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return "audio" in res.stdout
    except Exception as e:
        logger.error(f"Error checking audio stream: {e}")
        return True


def has_video_stream(filepath):
    """Checks if the media file has a video stream using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0", filepath
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return "video" in res.stdout
    except Exception as e:
        logger.error(f"Error checking video stream: {e}")
        return False


def apply_audio_effects(filepath, eq_bass=0, eq_lowmid=0, eq_highmid=0, eq_treble=0, speed=1.0, voice_preset="normal"):
    """Applies EQ filters, voice FX, and playback speed to the audio track of the media file using FFmpeg."""
    if not has_audio_stream(filepath):
        logger.info(f"Skipping audio effects for {filepath} because it has no audio stream.")
        return filepath

    logger.info(f"Applying audio filters to {filepath}: EQ({eq_bass}, {eq_lowmid}, {eq_highmid}, {eq_treble}), speed={speed}, voice={voice_preset}")
    base, ext = os.path.splitext(filepath)
    output_filepath = base + "_audio_fx" + ext

    audio_filters = []
    
    # EQ peaking filters matching Web Audio API
    try:
        b = float(eq_bass)
        if b != 0:
            audio_filters.append(f"equalizer=f=60:width_type=q:w=1.0:g={b}")
    except Exception as e:
        logger.error(f"Error parsing bass EQ: {e}")
    
    try:
        lm = float(eq_lowmid)
        if lm != 0:
            audio_filters.append(f"equalizer=f=500:width_type=q:w=1.0:g={lm}")
    except Exception as e:
        logger.error(f"Error parsing lowmid EQ: {e}")

    try:
        hm = float(eq_highmid)
        if hm != 0:
            audio_filters.append(f"equalizer=f=2000:width_type=q:w=1.0:g={hm}")
    except Exception as e:
        logger.error(f"Error parsing highmid EQ: {e}")

    try:
        t = float(eq_treble)
        if t != 0:
            audio_filters.append(f"equalizer=f=10000:width_type=q:w=1.0:g={t}")
    except Exception as e:
        logger.error(f"Error parsing treble EQ: {e}")

    # Voice FX filters matching applyVoiceEffectsNodePreset in JS
    if voice_preset == "deep":
        audio_filters.append("lowshelf=f=150:g=8:w=0.5")
        audio_filters.append("highshelf=f=3000:g=-8:w=0.5")
    elif voice_preset == "bright":
        audio_filters.append("lowshelf=f=200:g=-4:w=0.5")
        audio_filters.append("highshelf=f=4000:g=8:w=0.5")
    elif voice_preset == "hall":
        audio_filters.append("aecho=0.8:0.88:300:0.4")
    elif voice_preset == "studio":
        audio_filters.append("equalizer=f=120:width_type=q:w=1.0:g=2")
        audio_filters.append("equalizer=f=3200:width_type=q:w=1.0:g=3")
        audio_filters.append("aecho=0.8:0.88:300:0.08")
    elif voice_preset == "lofi":
        audio_filters.append("lowpass=f=3200")
        audio_filters.append("highpass=f=180")
    elif voice_preset == "telephone":
        audio_filters.append("highpass=f=450")
        audio_filters.append("lowpass=f=2800")
    elif voice_preset == "underwater":
        audio_filters.append("lowpass=f=600")
        audio_filters.append("aecho=0.8:0.88:300:0.2")

    # Playback Speed (tempo) filter
    try:
        s = float(speed)
        if s != 1.0 and s > 0:
            current_speed = s
            # atempo only accepts between 0.5 and 2.0. Chain multiple filters if out of bounds.
            while current_speed > 2.0:
                audio_filters.append("atempo=2.0")
                current_speed /= 2.0
            while current_speed < 0.5:
                audio_filters.append("atempo=0.5")
                current_speed /= 0.5
            if current_speed != 1.0:
                audio_filters.append(f"atempo={current_speed:.2f}")
    except Exception as speed_err:
        logger.error(f"Error parsing speed: {speed_err}")

    if not audio_filters:
        return filepath

    filter_str = ",".join(audio_filters)
    
    # Choose appropriate audio codec based on extension
    # We must re-encode audio to apply filters.
    ext_lower = ext.lower()
    if ext_lower == ".mp3":
        audio_codec = ["-c:a", "libmp3lame"]
    else:
        audio_codec = ["-c:a", "aac"]

    # If speed is not 1.0 and this is a video file, we must also speed up the video stream using setpts and re-encode the video.
    # Otherwise, we can copy the video stream if present to save CPU cycles.
    is_speed_change = False
    try:
        is_speed_change = (float(speed) != 1.0 and float(speed) > 0)
    except:
        pass

    if is_speed_change and has_video_stream(filepath):
        video_speed = float(speed)
        video_filters = f"setpts=1/{video_speed}*PTS"
        cmd = [
            "ffmpeg", "-y", "-i", filepath,
            "-vf", video_filters,
            "-af", filter_str,
            "-c:v", "libx264", "-preset", "superfast", "-crf", "23"
        ] + audio_codec + ["-map", "0:v?", "-map", "0:a", output_filepath]
    else:
        cmd = [
            "ffmpeg", "-y", "-i", filepath,
            "-af", filter_str,
            "-c:v", "copy"
        ] + audio_codec + ["-map", "0:v?", "-map", "0:a", output_filepath]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 0:
        os.remove(filepath)
        os.rename(output_filepath, filepath)
        return filepath
    else:
        logger.error(f"Audio effects application failed (code {res.returncode}). Stderr: {res.stderr}")
        if os.path.exists(output_filepath):
            os.remove(output_filepath)
        return filepath
