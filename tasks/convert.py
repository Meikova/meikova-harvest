import os
import re
import time
import logging
import threading
import subprocess
from config import TEMP_DOWNLOAD_DIR, downloads_status, downloads_status_lock

logger = logging.getLogger(__name__)

def get_media_duration(file_path):
    """Probes the media file to get its duration in seconds."""
    cmd = [
        "ffprobe", "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        file_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return float(res.stdout.strip())
    except Exception:
        # Fallback to parsing ffmpeg stderr
        cmd_ff = ["ffmpeg", "-i", file_path]
        try:
            res_ff = subprocess.run(cmd_ff, capture_output=True, text=True, timeout=5)
            match = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", res_ff.stderr)
            if match:
                h, m, s, ms = match.groups()
                return int(h) * 3600 + int(m) * 60 + int(s) + float(f"0.{ms}")
        except Exception:
            pass
    return None

def run_conversion(task_id, file_path, filename, target_format, options):
    try:
        logger.info(f"Starting conversion task {task_id} for file: {file_path}")
        
        # Get total duration for progress reporting
        total_duration = get_media_duration(file_path)
        logger.info(f"Source file duration: {total_duration} seconds")
        
        # Determine unique output path
        output_filename = f"converted_{task_id}.{target_format}"
        output_filepath = os.path.join(TEMP_DOWNLOAD_DIR, output_filename)
        
        # Build ffmpeg command based on options
        cmd = ["ffmpeg", "-y"]
        
        # Handle input file
        cmd.extend(["-i", file_path])
        
        # Handle format specific flags
        audio_bitrate = options.get("audio_bitrate", "320k")
        video_res = options.get("video_res", "original")
        
        # Video resolution filters
        video_filters = []
        if video_res != "original" and target_format in ["mp4", "mkv", "webm", "gif"]:
            if video_res == "1080p":
                video_filters.append("scale=1920:-2")
            elif video_res == "720p":
                video_filters.append("scale=1280:-2")
            elif video_res == "480p":
                video_filters.append("scale=854:-2")
        
        if target_format == "mp3":
            cmd.extend(["-vn", "-c:a", "libmp3lame", "-b:a", audio_bitrate])
        elif target_format == "wav":
            cmd.extend(["-vn", "-c:a", "pcm_s16le"])
        elif target_format == "flac":
            cmd.extend(["-vn", "-c:a", "flac"])
        elif target_format == "m4a":
            cmd.extend(["-vn", "-c:a", "aac", "-b:a", audio_bitrate])
        elif target_format == "mp4":
            cmd.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", audio_bitrate])
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])
        elif target_format == "mkv":
            cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-b:a", audio_bitrate])
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])
        elif target_format == "webm":
            cmd.extend(["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "30", "-c:a", "libopus", "-b:a", "128k"])
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])
        elif target_format == "gif":
            # High-quality 256-color GIF conversion via palettegen & paletteuse
            palette_path = os.path.join(TEMP_DOWNLOAD_DIR, f"palette_{task_id}.png")
            
            # Step 1: Generate palette
            gif_filters = ["fps=15"]
            if video_filters:
                gif_filters.extend(video_filters)
            gif_filters.append("palettegen")
            
            palette_cmd = ["ffmpeg", "-y", "-i", file_path, "-vf", ",".join(gif_filters), palette_path]
            logger.info(f"Generating GIF palette with command: {' '.join(palette_cmd)}")
            
            with downloads_status_lock:
                if task_id in downloads_status:
                    downloads_status[task_id].update({
                        "status": "processing",
                        "progress": 5,
                        "message": "Generating GIF color palette (Step 1/2)..."
                    })
            
            subprocess.run(palette_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            with downloads_status_lock:
                if task_id in downloads_status:
                    downloads_status[task_id].update({
                        "status": "processing",
                        "progress": 15,
                        "message": "Rendering high-quality GIF (Step 2/2)..."
                    })
            
            # Step 2: Convert to GIF using palette
            cmd = ["ffmpeg", "-y", "-i", file_path]
            if os.path.exists(palette_path):
                cmd.extend(["-i", palette_path])
                complex_filter = f"[0:v]fps=15"
                if video_filters:
                    complex_filter += f",{','.join(video_filters)}"
                complex_filter += "[v];[v][1:v]paletteuse"
                cmd.extend(["-filter_complex", complex_filter])
            else:
                simple_filters = ["fps=15"]
                if video_filters:
                    simple_filters.extend(video_filters)
                cmd.extend(["-vf", ",".join(simple_filters)])
        
        # Append target output file
        cmd.append(output_filepath)
        
        logger.info(f"Executing conversion command: {' '.join(cmd)}")
        
        # Run process and parse progress
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            encoding="utf-8",
            errors="ignore"
        )
        
        # Monitor progress via stderr output
        while True:
            line = process.stderr.readline()
            if not line:
                break
            
            # Parse time progress e.g., time=00:01:23.45
            match = re.search(r"time=(\d+):(\d+):(\d+)\.(\d+)", line)
            if match and total_duration:
                h, m, s, ms = match.groups()
                current_secs = int(h) * 3600 + int(m) * 60 + int(s) + float(f"0.{ms}")
                
                if target_format == "gif":
                    pct = min(99, 15 + int((current_secs / total_duration) * 84))
                    msg = f"Rendering high-quality GIF (Step 2/2)... {pct}%"
                else:
                    pct = min(99, int((current_secs / total_duration) * 100))
                    msg = f"Converting... {pct}%"
                
                with downloads_status_lock:
                    if task_id in downloads_status:
                        downloads_status[task_id].update({
                            "status": "processing",
                            "progress": pct,
                            "message": msg
                        })
        
        process.wait()
        
        # Clean up palette if GIF
        if target_format == "gif":
            palette_path = os.path.join(TEMP_DOWNLOAD_DIR, f"palette_{task_id}.png")
            if os.path.exists(palette_path):
                try:
                    os.remove(palette_path)
                except Exception:
                    pass
        
        if process.returncode == 0 and os.path.exists(output_filepath):
            logger.info(f"Conversion completed successfully for task {task_id}")
            with downloads_status_lock:
                if task_id in downloads_status:
                    downloads_status[task_id].update({
                        "status": "complete",
                        "progress": 100,
                        "message": "Conversion completed successfully.",
                        "filepath": output_filepath
                    })
        else:
            stderr_out = process.stderr.read()
            raise Exception(f"FFmpeg process returned exit code {process.returncode}. Stderr: {stderr_out}")
            
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
        # Clean up original uploaded file to save disk space
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up original uploaded file: {file_path}")
            except Exception as clean_err:
                logger.warning(f"Failed to clean up original uploaded file {file_path}: {clean_err}")

def start_conversion_task(task_id, file_path, filename, target_format, options):
    """Launches the format conversion task in a background thread."""
    thread = threading.Thread(
        target=run_conversion,
        args=(task_id, file_path, filename, target_format, options),
        daemon=True
    )
    thread.start()
