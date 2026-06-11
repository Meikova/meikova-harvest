import os
import logging
import subprocess

logger = logging.getLogger(__name__)

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
        
    cmd = ["ffmpeg", "-y"]
    if start and not is_zero_time(start):
        cmd.extend(["-ss", start])
    if end and not is_zero_time(end):
        cmd.extend(["-to", end])
        
    cmd.extend(["-i", filepath, "-c", "copy", output_filepath])
    
    logger.info(f"Running FFmpeg trim command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 0:
        logger.info("Trimming successful. Replacing original file.")
        try:
            os.remove(filepath)
            os.rename(output_filepath, filepath)
            return filepath
        except Exception as replace_err:
            logger.warning(f"Failed to replace trimmed file: {replace_err}")
            return output_filepath
    else:
        logger.warning(f"FFmpeg copy trim failed (code {result.returncode}). Stderr: {result.stderr}")
        cmd_transcode = ["ffmpeg", "-y"]
        if start and not is_zero_time(start):
            cmd_transcode.extend(["-ss", start])
        if end and not is_zero_time(end):
            cmd_transcode.extend(["-to", end])
        cmd_transcode.extend(["-i", filepath, output_filepath])
        logger.info(f"Running FFmpeg transcode trim fallback: {' '.join(cmd_transcode)}")
        res_trans = subprocess.run(cmd_transcode, capture_output=True, text=True)
        if res_trans.returncode == 0 and os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 0:
            logger.info("Transcode trim fallback successful. Replacing original file.")
            try:
                os.remove(filepath)
                os.rename(output_filepath, filepath)
                return filepath
            except Exception as replace_err:
                logger.warning(f"Failed to replace trimmed file: {replace_err}")
                return output_filepath
        else:
            logger.error(f"FFmpeg transcode trim also failed. Stderr: {res_trans.stderr}")
            if os.path.exists(output_filepath):
                try:
                    os.remove(output_filepath)
                except Exception:
                    pass
            return filepath
