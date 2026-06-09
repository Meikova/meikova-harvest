import os
import uuid
import shutil
import logging
import threading
from urllib.parse import quote
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
import yt_dlp
import static_ffmpeg

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Initialize static-ffmpeg to add portable binaries to PATH
logger.info("Initializing static-ffmpeg...")
try:
    static_ffmpeg.add_paths()
    logger.info("static-ffmpeg paths injected successfully.")
except Exception as e:
    logger.error(f"Failed to inject static-ffmpeg paths: {e}")

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

TEMP_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(TEMP_DOWNLOAD_DIR, exist_ok=True)

# Clean up any leftover temporary folders from previous runs on startup
logger.info("Cleaning up leftover temporary downloads...")
try:
    for item in os.listdir(TEMP_DOWNLOAD_DIR):
        item_path = os.path.join(TEMP_DOWNLOAD_DIR, item)
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
        else:
            os.remove(item_path)
    logger.info("Leftover temporary downloads cleaned.")
except Exception as e:
    logger.warning(f"Failed to clean downloads directory on startup: {e}")

# Global dictionary for tracking download tasks
downloads_status = {}
downloads_status_lock = threading.Lock()

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


@app.route("/")
def index():
    return render_template("index.html")


def format_duration(seconds):
    """Convert seconds to human-readable duration string."""
    if not seconds:
        return "Unknown"
    seconds = int(seconds)
    mins = seconds // 60
    secs = seconds % 60
    hours = mins // 60
    mins = mins % 60
    if hours > 0:
        return f"{hours:d}:{mins:02d}:{secs:02d}"
    return f"{mins:d}:{secs:02d}"


def format_size(size_bytes):
    """Convert bytes to human-readable size string."""
    if not size_bytes:
        return None
    size_bytes = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


@app.route("/api/info", methods=["POST"])
def get_info():
    data = request.get_json() or {}
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"status": "error", "message": "Link URL is required."}), 400

    logger.info(f"Fetching metadata for URL: {url}")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "noplaylist": True,
        "js_runtimes": {"deno": {}, "node": {}, "bun": {}, "quickjs": {}},
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            title = info.get("title", "Unknown Title")
            duration_sec = info.get("duration", 0)
            duration = format_duration(duration_sec)
            uploader = info.get("uploader", "Unknown Channel")
            thumbnail = info.get("thumbnail") or (
                info.get("thumbnails")[-1].get("url") if info.get("thumbnails") else None
            )

            # --- Rich Metadata extraction ---
            view_count = info.get("view_count")
            like_count = info.get("like_count")
            
            def format_count(count):
                if not count:
                    return "0"
                count = int(count)
                if count >= 1_000_000:
                    return f"{count / 1_000_000:.1f}M"
                if count >= 1_000:
                    return f"{count / 1_000:.1f}K"
                return str(count)
                
            views_label = format_count(view_count) if view_count else "Unknown"
            likes_label = format_count(like_count) if like_count else "Unknown"
            
            raw_date = info.get("upload_date")
            formatted_date = "Unknown"
            if raw_date and len(raw_date) == 8:
                try:
                    from datetime import datetime
                    formatted_date = datetime.strptime(raw_date, "%Y%m%d").strftime("%d %b %Y")
                except Exception:
                    pass
                    
            description = info.get("description") or "No description available."
            category = info.get("categories")[0] if info.get("categories") else None
            tags = info.get("tags")[:5] if info.get("tags") else []

            # --- Subtitles extraction ---
            subtitles = []
            # Manual subtitles
            raw_subs = info.get("subtitles") or {}
            for lang, formats in raw_subs.items():
                lang_name = formats[0].get("name") if formats else lang.upper()
                subtitles.append({
                    "lang_code": lang,
                    "name": lang_name,
                    "is_auto": False
                })
            # Auto captions (limit to common ones)
            raw_auto = info.get("automatic_captions") or {}
            preferred_auto_langs = ["vi", "en", "ja", "ko"]
            for lang in preferred_auto_langs:
                if lang in raw_auto and lang not in raw_subs:
                    formats = raw_auto[lang]
                    lang_name = (formats[0].get("name") if formats else lang.upper()) + " (Auto)"
                    subtitles.append({
                        "lang_code": lang,
                        "name": lang_name,
                        "is_auto": True
                    })

            formats_list = info.get("formats", [])
            is_shorts = "/shorts/" in url or (info.get("duration", 0) and info.get("duration", 0) <= 60)

            # --- Find best audio stream for size estimation ---
            best_audio_format = None
            for f in formats_list:
                if f.get("vcodec") == "none" and f.get("acodec") != "none":
                    if not best_audio_format or (f.get("tbr") or 0) > (best_audio_format.get("tbr") or 0):
                        best_audio_format = f

            best_audio_size = 0
            if best_audio_format:
                best_audio_size = best_audio_format.get("filesize") or best_audio_format.get("filesize_approx") or 0
                if not best_audio_size and duration_sec and best_audio_format.get("tbr"):
                    best_audio_size = int(duration_sec * best_audio_format.get("tbr") * 1000 / 8)
            if not best_audio_size and duration_sec:
                best_audio_size = int(duration_sec * 128 * 1000 / 8)

            # --- Build video options ---
            video_options = []
            added_resolutions = set()

            for f in formats_list:
                height = f.get("height")
                vcodec = f.get("vcodec")
                if height and vcodec and vcodec != "none":
                    res_label = f"{height}p"
                    if res_label not in added_resolutions:
                        v_size = f.get("filesize") or f.get("filesize_approx") or 0
                        if not v_size and duration_sec and f.get("tbr"):
                            v_size = int(duration_sec * f.get("tbr") * 1000 / 8)
                        total_size = (v_size + best_audio_size) if v_size else 0

                        video_options.append({
                            "format_id": f"bestvideo[height={height}]+bestaudio[ext=m4a]/bestvideo[height={height}]+bestaudio/best[height={height}]",
                            "resolution": res_label,
                            "ext": "mp4",
                            "type": "video",
                            "size": format_size(total_size),
                            "label": f"Video {res_label}"
                        })
                        added_resolutions.add(res_label)

            video_options.sort(key=lambda x: int(x["resolution"].replace("p", "")), reverse=True)

            if not video_options:
                video_options.append({
                    "format_id": "bestvideo+bestaudio/best",
                    "resolution": "Best",
                    "ext": "mp4",
                    "type": "video",
                    "size": None,
                    "label": "Video (Best Quality)"
                })

            # --- Build audio options ---
            audio_options = []
            
            # Native M4A (no conversion, ultra fast)
            est_m4a_size = format_size(best_audio_size) if best_audio_size else None
            audio_options.append({
                "format_id": "bestaudio[ext=m4a]/bestaudio",
                "resolution": "Audio",
                "ext": "m4a",
                "type": "audio",
                "size": est_m4a_size,
                "label": "M4A AAC (Original Quality - Fast)"
            })
            
            qualities = [
                ("320", "Ultra", "320kbps"),
                ("192", "High", "192kbps"),
                ("128", "Standard", "128kbps"),
            ]
            for q_val, q_name, q_label in qualities:
                est_size = format_size(int(duration_sec * int(q_val) * 1000 / 8)) if duration_sec else None
                audio_options.append({
                    "format_id": "bestaudio/best",
                    "resolution": "Audio",
                    "ext": "mp3",
                    "type": "audio",
                    "quality": q_val,
                    "size": est_size,
                    "label": f"MP3 {q_name} ({q_label})"
                })

            # --- Detect platform and source ---
            extractor = info.get("extractor_key", "").lower()
            platform_class = "default"
            
            if "youtube" in extractor:
                if "youtubekids.com" in url:
                    platform_label = "YouTube Kids"
                    platform_class = "youtube-kids"
                elif "music.youtube.com" in url:
                    platform_label = "YouTube Music"
                    platform_class = "youtube-music"
                elif "/shorts/" in url or (not info.get("is_live") and info.get("duration", 0) and info.get("duration", 0) <= 60):
                    platform_label = "YouTube Shorts"
                    platform_class = "youtube-shorts"
                elif "/live/" in url or info.get("is_live"):
                    platform_label = "YouTube Live"
                    platform_class = "youtube-live"
                elif "/clip/" in url:
                    platform_label = "YouTube Clip"
                    platform_class = "youtube-clip"
                elif "/embed/" in url or "/v/" in url or "youtube-nocookie.com" in url:
                    platform_label = "YouTube Embed"
                    platform_class = "youtube"
                elif "m.youtube.com" in url:
                    platform_label = "YouTube Mobile"
                    platform_class = "youtube"
                else:
                    platform_label = "YouTube"
                    platform_class = "youtube"
            elif "tiktok" in extractor:
                platform_label = "TikTok"
                platform_class = "tiktok"
            elif "facebook" in extractor:
                if "/reel/" in url or "/reels/" in url:
                    platform_label = "Facebook Reel"
                else:
                    platform_label = "Facebook"
                platform_class = "facebook"
            elif "instagram" in extractor:
                if "/reel/" in url or "/reels/" in url:
                    platform_label = "Instagram Reel"
                else:
                    platform_label = "Instagram"
                platform_class = "instagram"
            else:
                # Capitalize first letter of extractor
                raw_platform = info.get("extractor_key", "Video")
                platform_label = raw_platform.capitalize() if raw_platform else "Video"
                platform_class = "default"

            return jsonify({
                "status": "success",
                "title": title,
                "uploader": uploader,
                "duration": duration,
                "thumbnail": thumbnail,
                "is_shorts": is_shorts,
                "platform_label": platform_label,
                "platform_class": platform_class,
                "views": views_label,
                "likes": likes_label,
                "upload_date": formatted_date,
                "description": description,
                "category": category,
                "tags": tags,
                "video_options": video_options,
                "audio_options": audio_options,
                "subtitles": subtitles,
            })

    except Exception as e:
        logger.error(f"Error fetching metadata: {str(e)}")
        return jsonify({"status": "error", "message": f"Could not parse URL. {str(e)}"}), 500


def bg_download_task(download_id, url, format_id, ext, quality="192"):
    """Background thread task to download media via yt-dlp."""
    temp_dir = os.path.join(TEMP_DOWNLOAD_DIR, f"temp_{download_id}")
    os.makedirs(temp_dir, exist_ok=True)
    logger.info(f"Task {download_id}: Start download {url} (format={format_id}, ext={ext}, quality={quality})")

    # Track how many times 'finished' fires
    # For video: finished fires once for video stream, once for audio stream
    # For audio/combined: finished fires once
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

            with downloads_status_lock:
                if download_id in downloads_status:
                    cur = downloads_status[download_id].get("progress", 0)
                    downloads_status[download_id].update({
                        "status": "downloading",
                        "progress": max(cur, progress_val),
                        "message": msg,
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
                            # Check if this was a combined stream (both codecs present)
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

    ydl_opts = {
        "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
        "nocheckcertificate": True,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "progress_hooks": [progress_hook],
        "js_runtimes": {"deno": {}, "node": {}, "bun": {}, "quickjs": {}},
    }

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
        ydl_opts.update({
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [format_id],
        })
    else:
        ydl_opts.update({
            "format": format_id,
            "merge_output_format": "mp4",
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

            downloaded_files = os.listdir(temp_dir)
            if not downloaded_files:
                raise Exception("Download completed but no output file found.")

            filename = downloaded_files[0]
            filepath = os.path.join(temp_dir, filename)

            with downloads_status_lock:
                if download_id in downloads_status:
                    downloads_status[download_id].update({
                        "status": "complete",
                        "progress": 100,
                        "message": "Ready!",
                        "filepath": filepath,
                        "temp_dir": temp_dir,
                        "filename": filename,
                    })
                    logger.info(f"Task {download_id}: Complete. File: {filename}")

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


@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.get_json() or {}
    url = (data.get("url") or "").strip()
    format_id = (data.get("format_id") or "").strip()
    ext = (data.get("ext") or "mp4").strip()
    quality = (data.get("quality") or "192").strip()

    if not url or not format_id:
        return jsonify({"status": "error", "message": "URL and format_id are required."}), 400

    download_id = str(uuid.uuid4())

    with downloads_status_lock:
        downloads_status[download_id] = {
            "status": "pending",
            "progress": 0,
            "message": "Queued. Starting download...",
            "ext": ext,
            "filepath": None,
            "temp_dir": None,
            "filename": None,
            "error": None,
        }

    logger.info(f"Enqueued task {download_id} for {url}")
    thread = threading.Thread(target=bg_download_task, args=(download_id, url, format_id, ext, quality))
    thread.start()

    return jsonify({"status": "success", "download_id": download_id})


@app.route("/api/download/status/<download_id>", methods=["GET"])
def get_download_status(download_id):
    with downloads_status_lock:
        status_info = downloads_status.get(download_id)
    if not status_info:
        return jsonify({"status": "error", "message": "Download task not found."}), 404
    # Return a safe copy without internal paths
    return jsonify({
        "status": status_info["status"],
        "progress": status_info["progress"],
        "message": status_info["message"],
        "ext": status_info.get("ext", ""),
        "error": status_info.get("error"),
    })


@app.route("/api/download/file/<download_id>", methods=["GET"])
def get_download_file(download_id):
    with downloads_status_lock:
        status_info = downloads_status.get(download_id)

    if not status_info:
        return """
        <html>
            <head>
                <title>File Purged | EveryThingDownloader</title>
                <style>
                    body { background: #07080f; color: #8b9dc3; font-family: system-ui, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; text-align: center; }
                    .card { background: rgba(14, 17, 30, 0.55); border: 1px solid rgba(255, 255, 255, 0.06); padding: 32px; border-radius: 12px; max-width: 450px; box-shadow: 0 20px 50px rgba(0,0,0,0.5); backdrop-filter: blur(20px); }
                    h2 { color: #63b3ed; margin-top: 0; font-weight: 600; }
                    p { font-size: 0.9rem; line-height: 1.6; }
                </style>
            </head>
            <body>
                <div class="card">
                    <h2>File Purged from Server</h2>
                    <p>This file has already been downloaded and automatically deleted from the server storage to save disk space.</p>
                    <p>If you need another copy, please go back to the downloader page and click the <strong>Get</strong> button again to rebuild it.</p>
                </div>
            </body>
        </html>
        """, 404
    if status_info["status"] != "complete":
        return jsonify({"status": "error", "message": "File is not ready yet."}), 400

    filepath = status_info["filepath"]
    temp_dir = status_info["temp_dir"]
    filename = status_info["filename"]
    ext = filepath.rsplit(".", 1)[-1] if "." in filepath else "mp4"

    if not os.path.exists(filepath):
        return jsonify({"status": "error", "message": "File not found on server."}), 404

    file_size = os.path.getsize(filepath)

    def generate_chunks():
        try:
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    yield chunk
        finally:
            # Cleanup is handled by the 5-minute delayed timer to support retries and download manager calls
            pass

    fallback_filename = f"media.{ext}"
    encoded_filename = quote(filename)
    if ext == "mp3":
        content_type = "audio/mpeg"
    elif ext == "m4a":
        content_type = "audio/mp4"
    else:
        content_type = "video/mp4"

    headers = {
        "Content-Disposition": f'attachment; filename="{fallback_filename}"; filename*=UTF-8\'\'{encoded_filename}',
        "Content-Length": str(file_size),
        "Content-Type": content_type,
        "Cache-Control": "no-cache",
    }

    return Response(generate_chunks(), headers=headers)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
