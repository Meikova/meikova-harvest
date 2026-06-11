import os
import shutil
import logging
import threading
import subprocess
import re
import requests
import yt_dlp
try:
    from yt_dlp.networking.impersonate import ImpersonateTarget
except ImportError:
    ImpersonateTarget = None

from config import TEMP_DOWNLOAD_DIR, downloads_status, downloads_status_lock
from utils.helpers import get_referer_by_url
from utils.ffmpeg import trim_file_if_needed
from utils.ytdl import create_ydl_instance

logger = logging.getLogger(__name__)


def schedule_cleanup(temp_dir, download_id, delay=300):
    """Schedules a delayed cleanup of the downloaded files to allow browser retries/fallback downloads."""
    def cleanup():
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Delayed cleanup completed for task {download_id} (purged {temp_dir})")
        except Exception as e:
            logger.error(f"Delayed cleanup error for task {download_id}: {e}")
        with downloads_status_lock:
            downloads_status.pop(download_id, None)

    timer = threading.Timer(delay, cleanup)
    timer.daemon = True
    timer.start()


def bg_download_task(download_id, url, format_id, ext, quality="192", title="media", client_id=None, trim_start=None, trim_end=None, translate_subs=None):
    """Background thread task to download media via yt-dlp."""
    temp_dir = os.path.join(TEMP_DOWNLOAD_DIR, f"temp_{download_id}")
    os.makedirs(temp_dir, exist_ok=True)
    logger.info(f"Task {download_id}: Start download {url} (format={format_id}, ext={ext}, quality={quality})")

    # Direct CDN stream download bypass
    if format_id.startswith("direct_video") or format_id.startswith("direct_photo") or format_id.startswith("direct_audio"):
        try:
            with downloads_status_lock:
                if download_id in downloads_status:
                    downloads_status[download_id].update({
                        "status": "downloading",
                        "progress": 5,
                        "message": "Connecting to direct stream source..."
                    })
                    
            referer = get_referer_by_url(url)
            # Fallback for format_id check if referer defaults to facebook
            if referer == "https://www.facebook.com/" and "tiktok" in str(format_id).lower():
                referer = "https://www.tiktok.com/"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": referer
            }
            
            cookies_dict = {}
            if client_id:
                client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")
                if os.path.exists(client_cookies):
                    try:
                        with open(client_cookies, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                line = line.strip()
                                if not line or line.startswith('#'):
                                    continue
                                parts = line.split('\t')
                                if len(parts) >= 7:
                                    name = parts[5]
                                    value = parts[6]
                                    cookies_dict[name] = value
                        logger.info(f"Loaded {len(cookies_dict)} cookies for direct CDN download task.")
                    except Exception as cookie_err:
                        logger.warning(f"Failed to parse cookies file {client_cookies}: {cookie_err}")

            response = requests.get(url, headers=headers, cookies=cookies_dict, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            is_audio_requested = ext in ["mp3", "m4a"]
            if is_audio_requested:
                download_ext = "mp4"
                filepath = os.path.join(temp_dir, f"temp_source.mp4")
            else:
                download_ext = ext
                filepath = os.path.join(temp_dir, f"media.{ext}")
                
            downloaded = 0
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=16384):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            if percent % 5 == 0 or percent == 100:
                                with downloads_status_lock:
                                    if download_id in downloads_status:
                                        downloads_status[download_id].update({
                                            "progress": min(80 if is_audio_requested else 95, percent),
                                            "message": f"Downloading direct file: {percent}%"
                                        })
                                        
            # Extract audio if requested
            if is_audio_requested:
                with downloads_status_lock:
                    if download_id in downloads_status:
                        downloads_status[download_id].update({
                            "progress": 85,
                            "message": "Extracting audio track..."
                        })
                        
                final_filepath = os.path.join(temp_dir, f"media.{ext}")
                
                if ext == "m4a":
                    # Try copying audio track directly
                    cmd = ["ffmpeg", "-y", "-i", filepath, "-vn", "-acodec", "copy", final_filepath]
                    res_cmd = subprocess.run(cmd, capture_output=True)
                    if res_cmd.returncode != 0:
                        logger.warning("ffmpeg audio copy failed, re-encoding to m4a...")
                        cmd = ["ffmpeg", "-y", "-i", filepath, "-vn", "-c:a", "aac", "-b:a", "192k", final_filepath]
                        subprocess.run(cmd, capture_output=True)
                else: # mp3
                    cmd = ["ffmpeg", "-y", "-i", filepath, "-vn", "-c:a", "libmp3lame", "-b:a", f"{quality}k", final_filepath]
                    subprocess.run(cmd, capture_output=True)
                    
                # Delete temp video source file
                try:
                    os.remove(filepath)
                except Exception:
                    pass
                    
                filepath = final_filepath
            
            if (trim_start or trim_end) and ext != "vtt":
                try:
                    filepath = trim_file_if_needed(filepath, trim_start, trim_end)
                except Exception as trim_err:
                    logger.error(f"Error during direct file trimming: {trim_err}")
            
            def sanitize_filename(name):
                cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
                return cleaned[:80].strip() or "media"

            safe_title = sanitize_filename(title)
            user_filename = f"{safe_title}.{ext}"

            with downloads_status_lock:
                if download_id in downloads_status:
                    downloads_status[download_id].update({
                        "status": "complete",
                        "progress": 100,
                        "message": "Ready!",
                        "filepath": filepath,
                        "temp_dir": temp_dir,
                        "filename": user_filename,
                    })
                    logger.info(f"Task {download_id}: Complete. File: {user_filename}")
            
            schedule_cleanup(temp_dir, download_id, delay=300)
            return
            
        except Exception as e:
            logger.error(f"Direct download failed for task {download_id}: {e}")
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
            with downloads_status_lock:
                if download_id in downloads_status:
                    downloads_status[download_id].update({
                        "status": "error",
                        "progress": 0,
                        "message": f"Download failed: {str(e)}",
                        "error": str(e),
                    })
            return

    # Track how many times 'finished' fires
    finished_count = [0]

    def progress_hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            pct = int((downloaded / total) * 100) if total > 0 else 0

            info = d.get("info_dict") or {}
            vcodec = info.get("vcodec")
            acodec = info.get("acodec")

            if ext in ["mp3", "m4a"]:
                # Audio-only: single stream, 0-90%
                progress_val = int(pct * 0.90)
                msg = f"Downloading audio stream: {pct}%"
            elif ext == "vtt":
                # Subtitle-only: single stream, 0-90%
                progress_val = int(pct * 0.90)
                msg = f"Downloading subtitles: {pct}%"
            else:
                is_video_only = (vcodec and vcodec != "none") and (not acodec or acodec == "none")
                is_audio_only = (not vcodec or vcodec == "none") and (acodec and acodec != "none")

                if is_video_only:
                    # Video stream (part 1/2): 0-70%
                    progress_val = int(pct * 0.70)
                    msg = f"Downloading video stream (1/2): {pct}%"
                elif is_audio_only:
                    # Audio stream (part 2/2): 70-90%
                    progress_val = 70 + int(pct * 0.20)
                    msg = f"Downloading audio stream (2/2): {pct}%"
                else:
                    # Combined/muxed stream: 0-90%
                    progress_val = int(pct * 0.90)
                    msg = f"Downloading: {pct}%"

            speed_bytes = d.get("speed")
            speed_str = ""
            if speed_bytes is not None:
                if speed_bytes > 1024 * 1024:
                    speed_str = f"{speed_bytes / (1024 * 1024):.1f} MB/s"
                elif speed_bytes > 1024:
                    speed_str = f"{speed_bytes / 1024:.1f} KB/s"
                else:
                    speed_str = f"{speed_bytes:.0f} B/s"

            eta_seconds = d.get("eta")
            eta_str = ""
            if eta_seconds is not None:
                if eta_seconds > 60:
                    m = int(eta_seconds // 60)
                    s = int(eta_seconds % 60)
                    eta_str = f"{m}m {s}s"
                else:
                    eta_str = f"{eta_seconds}s"

            with downloads_status_lock:
                if download_id in downloads_status:
                    cur = downloads_status[download_id].get("progress", 0)
                    downloads_status[download_id].update({
                        "status": "downloading",
                        "progress": max(cur, progress_val),
                        "message": msg,
                        "speed": speed_str,
                        "eta": eta_str,
                    })

        elif d["status"] == "finished":
            finished_count[0] += 1
            with downloads_status_lock:
                if download_id in downloads_status:
                    if ext == "mp3":
                        # Audio: single stream done → encoding to MP3
                        downloads_status[download_id].update({
                            "status": "processing",
                            "progress": 95,
                            "message": "Converting to MP3...",
                        })
                    elif ext == "m4a":
                        # M4A: single stream done → finalizing (no conversion)
                        downloads_status[download_id].update({
                            "status": "processing",
                            "progress": 98,
                            "message": "Finalizing...",
                        })
                    elif ext == "vtt":
                        # Subtitles: single stream done → finalizing
                        downloads_status[download_id].update({
                            "status": "processing",
                            "progress": 98,
                            "message": "Finalizing subtitles...",
                        })
                    else:
                        if finished_count[0] == 1:
                            # First stream (video) done, audio coming next
                            info = d.get("info_dict") or {}
                            vcodec = info.get("vcodec")
                            acodec = info.get("acodec")
                            is_combined = (vcodec and vcodec != "none") and (acodec and acodec != "none")
                            if is_combined:
                                # Combined stream — no merge needed
                                downloads_status[download_id].update({
                                    "status": "processing",
                                    "progress": 98,
                                    "message": "Finalizing...",
                                })
                            else:
                                # Video-only stream done → audio download starting
                                downloads_status[download_id].update({
                                    "status": "downloading",
                                    "progress": 70,
                                    "message": "Video stream complete. Downloading audio...",
                                })
                        else:
                            # Second stream (audio) done → merging
                            downloads_status[download_id].update({
                                "status": "merging",
                                "progress": 95,
                                "message": "Merging video and audio streams...",
                            })

    is_youtube = any(domain in url.lower() for domain in ["youtube.com", "youtu.be"])
    ydl_opts = {
        "outtmpl": os.path.join(temp_dir, "media.%(ext)s"),
        "nocheckcertificate": True,
        "verbose": is_youtube,
        "quiet": not is_youtube,
        "no_warnings": not is_youtube,
        "noplaylist": True,
        "progress_hooks": [progress_hook],
        "js_runtimes": {"deno": {}, "node": {}, "bun": {}, "quickjs": {}},
        "cookiesfrombrowser": "auto",
        "ignoreerrors": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["default"],
            }
        },
    }
    if ImpersonateTarget:
        try:
            ydl_opts["impersonate"] = ImpersonateTarget.from_str("chrome")
        except Exception as e:
            logger.warning(f"Could not set impersonate option in bg_download_task: {e}")

    if ext == "mp3":
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality,
            }],
            "postprocessor_args": {
                "extractaudio": ["-compression_level", "9", "-threads", "0"]
            }
        })
    elif ext == "m4a":
        ydl_opts.update({
            "format": "bestaudio[ext=m4a]/bestaudio",
        })
    elif ext == "vtt":
        lang = "vi" if translate_subs == "vi" else format_id
        ydl_opts.update({
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [lang],
        })
    else:
        ydl_opts.update({
            "format": format_id,
            "merge_output_format": "mp4",
        })

    try:
        try:
            with create_ydl_instance(ydl_opts, url, client_id) as ydl:
                ret_code = ydl.download([url])
                if ret_code != 0:
                    raise Exception(f"yt-dlp download returned non-zero code {ret_code}")
        except Exception as e:
            logger.warning(f"Download with cookies failed: {e}. Retrying without cookies...")
            ydl_opts_no_cookies = ydl_opts.copy()
            ydl_opts_no_cookies.pop("cookiefile", None)
            ydl_opts_no_cookies.pop("cookiesfrombrowser", None)
            with yt_dlp.YoutubeDL(ydl_opts_no_cookies) as ydl_nocookies:
                ret_nocookies = ydl_nocookies.download([url])
                if ret_nocookies != 0:
                    raise Exception(f"Fallback download also failed with code {ret_nocookies}")

        downloaded_files = os.listdir(temp_dir)
        if not downloaded_files:
            raise Exception("Download completed but no output file found.")

        filename_on_disk = downloaded_files[0]
        filepath = os.path.join(temp_dir, filename_on_disk)

        # Call trim if requested
        if (trim_start or trim_end) and ext != "vtt":
            try:
                filepath = trim_file_if_needed(filepath, trim_start, trim_end)
                filename_on_disk = os.path.basename(filepath)
            except Exception as trim_err:
                logger.error(f"Error during file trimming: {trim_err}")

        def sanitize_filename(name):
            cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
            return cleaned[:80].strip() or "media"

        safe_title = sanitize_filename(title)
        if ext == "vtt":
            lang = "vi" if translate_subs == "vi" else format_id
            user_filename = f"{safe_title}.{lang}.vtt"
        else:
            user_filename = f"{safe_title}.{ext}"

        with downloads_status_lock:
            if download_id in downloads_status:
                downloads_status[download_id].update({
                    "status": "complete",
                    "progress": 100,
                    "message": "Ready!",
                    "filepath": filepath,
                    "temp_dir": temp_dir,
                    "filename": user_filename,
                })
                logger.info(f"Task {download_id}: Complete. File: {user_filename}")

        # Clean up the file 5 minutes (300 seconds) after completion
        schedule_cleanup(temp_dir, download_id, delay=300)

    except Exception as e:
        logger.error(f"Task {download_id} failed: {str(e)}")
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
        with downloads_status_lock:
            if download_id in downloads_status:
                downloads_status[download_id].update({
                    "status": "error",
                    "progress": 0,
                    "message": f"Download failed: {str(e)}",
                    "error": str(e),
                })
