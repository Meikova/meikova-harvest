import os
import re
import sys
import time
import json
import logging
import threading
import subprocess
from config import TEMP_DOWNLOAD_DIR, downloads_status, downloads_status_lock

logger = logging.getLogger(__name__)

def probe_media_file(file_path):
    """Probes the media file using ffprobe to retrieve duration, codecs, streams, and dimensions."""
    if not file_path or not os.path.exists(file_path):
        return None

    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        file_path
    ]
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8, creationflags=creationflags)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            format_info = data.get("format", {})
            streams = data.get("streams", [])
            
            video_stream = next((s for s in streams if s.get("codec_type") == "video" and s.get("codec_name") not in ["png", "jpg", "jpeg", "mjpeg", "bmp", "tiff"]), None)
            image_stream = next((s for s in streams if s.get("codec_type") == "video" and s.get("codec_name") in ["png", "jpg", "jpeg", "mjpeg", "bmp", "tiff", "webp"]), None)
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
            
            is_image = video_stream is None and image_stream is not None
            has_video = video_stream is not None
            has_audio = audio_stream is not None
            
            duration = float(format_info.get("duration") or (video_stream.get("duration") if video_stream else 0) or (audio_stream.get("duration") if audio_stream else 0) or 0)
            
            target_stream = video_stream or image_stream
            width = int(target_stream.get("width")) if target_stream and target_stream.get("width") else None
            height = int(target_stream.get("height")) if target_stream and target_stream.get("height") else None
            
            res_label = None
            if width and height:
                if height >= 2160 or width >= 3840:
                    res_label = "4K Ultra HD"
                elif height >= 1440 or width >= 2560:
                    res_label = "2K Quad HD"
                elif height >= 1080 or width >= 1920:
                    res_label = "1080p Full HD"
                elif height >= 720 or width >= 1280:
                    res_label = "720p HD"
                elif height >= 480:
                    res_label = "480p SD"
                else:
                    res_label = f"{width}x{height}"

            # Format duration into mm:ss or hh:mm:ss
            if is_image:
                duration_str = "Static Image"
            else:
                mins, secs = divmod(int(duration), 60)
                hrs, mins = divmod(mins, 60)
                duration_str = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs > 0 else f"{mins:02d}:{secs:02d}"

            size_bytes = os.path.getsize(file_path)
            size_mb = f"{size_bytes / (1024 * 1024):.1f} MB" if size_bytes < 1024 * 1024 * 1024 else f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

            return {
                "is_image": is_image,
                "has_video": has_video,
                "has_audio": has_audio,
                "duration": duration,
                "duration_formatted": duration_str,
                "width": width,
                "height": height,
                "resolution": res_label,
                "video_codec": video_stream.get("codec_name") if video_stream else (image_stream.get("codec_name") if image_stream else None),
                "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
                "audio_sample_rate": audio_stream.get("sample_rate") if audio_stream else None,
                "audio_channels": audio_stream.get("channels") if audio_stream else None,
                "format_name": format_info.get("format_name", ""),
                "size_bytes": size_bytes,
                "size_formatted": size_mb
            }
    except Exception as e:
        logger.warning(f"ffprobe probe failed for {file_path}: {e}")

    # Fallback duration parser
    dur = get_media_duration(file_path) or 0
    mins, secs = divmod(int(dur), 60)
    hrs, mins = divmod(mins, 60)
    duration_str = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs > 0 else f"{mins:02d}:{secs:02d}"
    sz = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    return {
        "has_video": True,
        "has_audio": True,
        "duration": dur,
        "duration_formatted": duration_str,
        "width": None,
        "height": None,
        "resolution": None,
        "video_codec": None,
        "audio_codec": None,
        "audio_sample_rate": None,
        "audio_channels": None,
        "format_name": "",
        "size_bytes": sz,
        "size_formatted": f"{sz / (1024 * 1024):.1f} MB"
    }


def get_media_duration(file_path):
    """Probes the media file to get its duration in seconds."""
    cmd = [
        "ffprobe", "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        file_path
    ]
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5, creationflags=creationflags)
        val = res.stdout.strip()
        if val and val != "N/A":
            return float(val)
    except Exception:
        pass
    
    # Fallback to parsing ffmpeg stderr
    cmd_ff = ["ffmpeg", "-i", file_path]
    try:
        res_ff = subprocess.run(cmd_ff, capture_output=True, text=True, timeout=5, creationflags=creationflags)
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", res_ff.stderr)
        if match:
            h, m, s, ms = match.groups()
            return int(h) * 3600 + int(m) * 60 + int(s) + float(f"0.{ms}")
    except Exception:
        pass
    return None


def run_conversion(task_id, file_path, filename, target_format, options):
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
    target_format = target_format.lower().strip()
    try:
        logger.info(f"Starting conversion task {task_id} for file: {file_path} -> {target_format}")
        
        # Probe media file for rich stream characteristics
        probe_info = probe_media_file(file_path) or {}
        has_video = probe_info.get("has_video", True)
        has_audio = probe_info.get("has_audio", True)
        total_duration = probe_info.get("duration") or get_media_duration(file_path) or 0
        logger.info(f"Source: video={has_video}, audio={has_audio}, duration={total_duration}s")
        
        # Determine unique output path
        output_filename = f"converted_{task_id}.{target_format}"
        output_filepath = os.path.join(TEMP_DOWNLOAD_DIR, output_filename)
        
        cmd = ["ffmpeg", "-y"]
        
        # Handle Trimming (start and end points)
        trim_start = options.get("trim_start")
        trim_end = options.get("trim_end")
        if trim_start:
            cmd.extend(["-ss", str(trim_start).strip()])

        # Handle Audio-only input converted to Video container
        is_audio_target = target_format in ["mp3", "wav", "flac", "m4a", "ogg", "opus"]
        is_animation_target = target_format in ["gif"]
        is_video_target = target_format in ["mp4", "mkv", "webm", "mov", "avi", "ts"]
        is_image_target = target_format in ["png", "jpg", "jpeg", "ico", "bmp", "tiff", "avif"] or (target_format == "webp" and is_source_image)
        is_source_image = probe_info.get("is_image", False)

        if is_audio_target and not has_audio:
            raise ValueError("Tập tin nguồn không chứa luồng âm thanh để chuyển đổi sang định dạng âm thanh.")

        if is_source_image and is_video_target:
            # Loop image for 5 seconds into video
            cmd.extend([
                "-loop", "1",
                "-i", file_path,
                "-t", "5"
            ])
            total_duration = 5.0
        elif not has_video and not is_source_image and is_video_target:
            # Generate a solid 1080p canvas with audio
            logger.info("Audio-only input detected for video export. Adding black 1080p background canvas.")
            cmd.extend([
                "-f", "lavfi", "-i", "color=c=0x0f172a:s=1920x1080:r=24",
                "-i", file_path,
                "-shortest"
            ])
        else:
            cmd.extend(["-i", file_path])

        if trim_end and not is_source_image:
            cmd.extend(["-to", str(trim_end).strip()])

        # Options parsing
        audio_bitrate = options.get("audio_bitrate", "320k")
        video_res = options.get("video_res", "original")
        video_fps = options.get("video_fps", "original")
        video_crf = options.get("video_crf", "23")
        video_codec = options.get("video_codec", "auto")
        audio_channels = options.get("audio_channels", "original")
        audio_volume = options.get("audio_volume", "100")
        mute_audio = options.get("mute_audio", False)
        is_passthrough = video_codec == "copy" or options.get("passthrough", False)
        has_usable_audio = has_audio and not mute_audio

        # Video filters list
        video_filters = []
        if is_source_image and is_video_target and video_res == "original":
            # Ensure width and height are divisible by 2 for yuv420p video codecs
            video_filters.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")
        elif video_res != "original" and (is_video_target or is_animation_target):
            if video_res == "4k":
                video_filters.append("scale=3840:-2:flags=lanczos")
            elif video_res == "2k":
                video_filters.append("scale=2560:-2:flags=lanczos")
            elif video_res == "1080p":
                video_filters.append("scale=1920:-2:flags=lanczos")
            elif video_res == "720p":
                video_filters.append("scale=1280:-2:flags=lanczos")
            elif video_res == "480p":
                video_filters.append("scale=854:-2:flags=lanczos")
            elif video_res == "360p":
                video_filters.append("scale=640:-2:flags=lanczos")

        if video_fps != "original" and video_fps in ["60", "30", "24", "15"]:
            video_filters.append(f"fps={video_fps}")

        # Audio filters list
        audio_filters = []
        if str(audio_volume) != "100" and audio_volume:
            try:
                vol_factor = float(audio_volume) / 100.0
                audio_filters.append(f"volume={vol_factor:.2f}")
            except Exception:
                pass

        # Build FFmpeg codec & container flags
        if is_passthrough and is_video_target:
            logger.info("Fast Remux (Stream Copy) requested.")
            cmd.extend(["-c", "copy"])
            if not has_usable_audio:
                cmd.append("-an")
        elif target_format == "mp3":
            cmd.extend(["-vn", "-c:a", "libmp3lame", "-b:a", audio_bitrate])
            if audio_channels == "mono":
                cmd.extend(["-ac", "1"])
            elif audio_channels == "stereo":
                cmd.extend(["-ac", "2"])
            if audio_filters:
                cmd.extend(["-filter:a", ",".join(audio_filters)])
        elif target_format == "wav":
            cmd.extend(["-vn", "-c:a", "pcm_s16le"])
            if audio_channels == "mono":
                cmd.extend(["-ac", "1"])
            elif audio_channels == "stereo":
                cmd.extend(["-ac", "2"])
            if audio_filters:
                cmd.extend(["-filter:a", ",".join(audio_filters)])
        elif target_format == "flac":
            cmd.extend(["-vn", "-c:a", "flac"])
            if audio_channels == "mono":
                cmd.extend(["-ac", "1"])
            elif audio_channels == "stereo":
                cmd.extend(["-ac", "2"])
            if audio_filters:
                cmd.extend(["-filter:a", ",".join(audio_filters)])
        elif target_format == "m4a":
            cmd.extend(["-vn", "-c:a", "aac", "-b:a", audio_bitrate])
            if audio_channels == "mono":
                cmd.extend(["-ac", "1"])
            elif audio_channels == "stereo":
                cmd.extend(["-ac", "2"])
            if audio_filters:
                cmd.extend(["-filter:a", ",".join(audio_filters)])
        elif target_format == "ogg":
            cmd.extend(["-vn", "-c:a", "libvorbis", "-q:a", "6"])
            if audio_channels == "mono":
                cmd.extend(["-ac", "1"])
            elif audio_channels == "stereo":
                cmd.extend(["-ac", "2"])
            if audio_filters:
                cmd.extend(["-filter:a", ",".join(audio_filters)])
        elif target_format == "opus":
            cmd.extend(["-vn", "-c:a", "libopus", "-b:a", audio_bitrate if audio_bitrate in ["128k", "192k"] else "160k"])
            if audio_channels == "mono":
                cmd.extend(["-ac", "1"])
            elif audio_channels == "stereo":
                cmd.extend(["-ac", "2"])
            if audio_filters:
                cmd.extend(["-filter:a", ",".join(audio_filters)])
        elif target_format == "mp4":
            v_codec = "libx265" if video_codec == "hevc" else "libx264"
            cmd.extend(["-c:v", v_codec, "-crf", str(video_crf), "-pix_fmt", "yuv420p"])
            if is_source_image:
                cmd.extend(["-preset", "veryfast"])
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])
            if not has_usable_audio:
                cmd.append("-an")
            else:
                cmd.extend(["-c:a", "aac", "-b:a", audio_bitrate])
                if audio_channels == "mono":
                    cmd.extend(["-ac", "1"])
                elif audio_channels == "stereo":
                    cmd.extend(["-ac", "2"])
                if audio_filters:
                    cmd.extend(["-filter:a", ",".join(audio_filters)])
        elif target_format == "mkv":
            v_codec = "libx265" if video_codec == "hevc" else "libx264"
            cmd.extend(["-c:v", v_codec, "-crf", str(video_crf)])
            if is_source_image:
                cmd.extend(["-preset", "veryfast"])
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])
            if not has_usable_audio:
                cmd.append("-an")
            else:
                cmd.extend(["-c:a", "aac", "-b:a", audio_bitrate])
                if audio_channels == "mono":
                    cmd.extend(["-ac", "1"])
                elif audio_channels == "stereo":
                    cmd.extend(["-ac", "2"])
                if audio_filters:
                    cmd.extend(["-filter:a", ",".join(audio_filters)])
        elif target_format == "webm":
            cmd.extend(["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", str(int(video_crf) + 8)])
            if is_source_image:
                cmd.extend(["-deadline", "realtime", "-cpu-used", "4"])
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])
            if not has_usable_audio:
                cmd.append("-an")
            else:
                cmd.extend(["-c:a", "libopus", "-b:a", "128k"])
                if audio_filters:
                    cmd.extend(["-filter:a", ",".join(audio_filters)])
        elif target_format == "mov":
            cmd.extend(["-c:v", "libx264", "-crf", str(video_crf), "-pix_fmt", "yuv420p"])
            if is_source_image:
                cmd.extend(["-preset", "veryfast"])
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])
            if not has_usable_audio:
                cmd.append("-an")
            else:
                cmd.extend(["-c:a", "aac", "-b:a", audio_bitrate])
                if audio_filters:
                    cmd.extend(["-filter:a", ",".join(audio_filters)])
        elif target_format == "avi":
            cmd.extend(["-c:v", "mpeg4", "-vtag", "xvid", "-qscale:v", "4"])
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])
            if not has_usable_audio:
                cmd.append("-an")
            else:
                cmd.extend(["-c:a", "libmp3lame", "-b:a", "192k"])
                if audio_filters:
                    cmd.extend(["-filter:a", ",".join(audio_filters)])
        elif target_format == "ts":
            cmd.extend(["-c:v", "libx264", "-crf", str(video_crf)])
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])
            if not has_usable_audio:
                cmd.append("-an")
            else:
                cmd.extend(["-c:a", "aac", "-b:a", audio_bitrate])
                if audio_filters:
                    cmd.extend(["-filter:a", ",".join(audio_filters)])
        elif target_format == "gif":
            # High-fidelity single-pass 256-color palette rendering
            gif_fps = options.get("gif_fps", "15")
            gif_scale = options.get("gif_scale", "480")
            
            filter_chain = [f"fps={gif_fps}"]
            if gif_scale and gif_scale != "original":
                filter_chain.append(f"scale={gif_scale}:-1:flags=lanczos")
            elif video_filters:
                filter_chain.extend(video_filters)
            
            filter_str = ",".join(filter_chain)
            complex_filter = f"{filter_str},split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3"
            cmd.extend(["-vf", complex_filter])
        elif target_format == "webp":
            if is_source_image:
                cmd.extend(["-vcodec", "libwebp", "-lossless", "0", "-q:v", "85"])
                if video_filters:
                    cmd.extend(["-filter:v", ",".join(video_filters)])
            else:
                # Modern animated WebP
                gif_fps = options.get("gif_fps", "15")
                webp_filters = [f"fps={gif_fps}"]
                if video_filters:
                    webp_filters.extend(video_filters)
                cmd.extend([
                    "-vcodec", "libwebp",
                    "-filter:v", ",".join(webp_filters),
                    "-lossless", "0",
                    "-q:v", "75",
                    "-loop", "0",
                    "-an"
                ])
        elif target_format == "png":
            cmd.extend(["-c:v", "png"])
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])
        elif target_format in ["jpg", "jpeg"]:
            cmd.extend(["-c:v", "mjpeg", "-q:v", "2"])
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])
        elif target_format == "ico":
            ico_filters = ["scale=256:256"]
            if video_filters:
                ico_filters.extend(video_filters)
            cmd.extend(["-vf", ",".join(ico_filters)])
        elif target_format == "bmp":
            cmd.extend(["-c:v", "bmp"])
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])
        elif target_format == "tiff":
            cmd.extend(["-c:v", "tiff"])
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])

        # Append final destination path
        cmd.append(output_filepath)
        
        logger.info(f"Executing conversion command: {' '.join(cmd)}")
        
        # Start conversion process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            encoding="utf-8",
            errors="ignore",
            creationflags=creationflags
        )
        
        # Monitor progress via stderr output
        stderr_tail = []
        while True:
            line = process.stderr.readline()
            if not line:
                break
            stderr_tail.append(line)
            if len(stderr_tail) > 40:
                stderr_tail.pop(0)
            
            match = re.search(r"time=(\d+):(\d+):(\d+)\.(\d+)", line)
            if match and total_duration:
                h, m, s, ms = match.groups()
                current_secs = int(h) * 3600 + int(m) * 60 + int(s) + float(f"0.{ms}")
                
                pct = min(99, max(1, int((current_secs / total_duration) * 100)))
                msg = f"Converting to {target_format.upper()}... {pct}%"
                
                with downloads_status_lock:
                    if task_id in downloads_status:
                        downloads_status[task_id].update({
                            "status": "processing",
                            "progress": pct,
                            "message": msg
                        })
        
        process.wait()
        
        if process.returncode == 0 and os.path.exists(output_filepath):
            logger.info(f"Conversion completed successfully for task {task_id}")
            with downloads_status_lock:
                if task_id in downloads_status:
                    downloads_status[task_id].update({
                        "status": "complete",
                        "progress": 100,
                        "message": f"Successfully converted to {target_format.upper()}.",
                        "filepath": output_filepath
                    })
        else:
            stderr_out = "".join(stderr_tail).strip()
            raise Exception(f"FFmpeg returned code {process.returncode}. Stderr: {stderr_out[:800]}")
            
    except Exception as e:
        logger.error(f"Error in conversion task {task_id}: {e}")
        with downloads_status_lock:
            if task_id in downloads_status:
                downloads_status[task_id].update({
                    "status": "error",
                    "progress": 0,
                    "message": f"Conversion failed: {str(e)}",
                    "error": str(e)
                })
    finally:
        # CRITICAL SAFETY CHECK:
        # ONLY delete the input file if it is an uploaded temporary file inside UPLOAD_DIR!
        # NEVER delete the user's original local media file!
        try:
            from routes.convert import UPLOAD_DIR
            abs_fp = os.path.abspath(file_path)
            abs_up = os.path.abspath(UPLOAD_DIR)
            if abs_fp.startswith(abs_up) and os.path.exists(abs_fp):
                os.remove(abs_fp)
                logger.info(f"Safely cleaned up temporary uploaded file: {abs_fp}")
        except Exception as clean_err:
            logger.warning(f"Failed to clean up upload file: {clean_err}")


def start_conversion_task(task_id, file_path, filename, target_format, options):
    """Launches the format conversion task in a background worker thread."""
    thread = threading.Thread(
        target=run_conversion,
        args=(task_id, file_path, filename, target_format, options),
        daemon=True
    )
    thread.start()
