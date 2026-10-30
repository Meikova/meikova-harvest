import os
import sys
import subprocess
import uuid
import logging
import threading
import shutil
import re
import io
import zipfile
import requests
import json
import time
from urllib.parse import quote
from flask import Blueprint, request, jsonify, send_file, Response, redirect

from config import TEMP_DOWNLOAD_DIR, downloads_status, downloads_status_lock
from routes.auth import get_authenticated_user
from utils.helpers import get_referer_by_url
from utils.cookies import get_cookie_file_path
from tasks import bg_download_task

download_bp = Blueprint("download", __name__)
logger = logging.getLogger(__name__)

DEFAULT_MEDIA_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"

FALLBACK_IMAGE_PLACEHOLDER_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400" fill="#0f172a">'
    '<rect width="600" height="400" fill="#0f172a" rx="8"/>'
    '<g transform="translate(268, 140)" fill="none" stroke="#64748b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="0" y="0" width="64" height="64" rx="8"/>'
    '<circle cx="20" cy="20" r="6"/>'
    '<path d="m64 44-18-18-36 36"/>'
    '</g>'
    '<text x="300" y="245" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="14" fill="#94a3b8" text-anchor="middle">Image unavailable or expired</text>'
    '</svg>'
)


def check_task_ownership(task_info):
    """Verifies that the current request has permission to access or mutate this task."""
    if not task_info:
        return True, None
    task_user_id = task_info.get("user_id")
    if not task_user_id:
        return True, None
    current_user = get_authenticated_user()
    user_id = current_user["id"] if current_user else None
    if task_user_id != user_id:
        return False, (jsonify({"status": "error", "message": "Access denied: You do not own this download task."}), 403)
    return True, None


@download_bp.route("/api/download", methods=["POST"])
def start_download():
    from utils.ratelimit import get_client_ip, check_rate_limit
    client_ip = get_client_ip(request)
    allowed, limit_msg = check_rate_limit(client_ip, "download")
    if not allowed:
        return jsonify({"status": "error", "message": limit_msg, "code": "RATE_LIMIT_EXCEEDED"}), 429

    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if "tiktok.com" in url.lower() and "/photo/" in url.lower():
        url = re.sub(r'/photo/', '/video/', url, flags=re.IGNORECASE)
    format_id = (data.get("format_id") or "").strip()
    ext = (data.get("ext") or "mp4").strip()
    quality = (data.get("quality") or "192").strip()
    title = (data.get("title") or "media").strip()
    thumbnail = (data.get("thumbnail") or "").strip()
    client_id = data.get("client_id")
    episode = (data.get("episode") or "").strip()
    server = (data.get("server") or "").strip()

    trim_start = data.get("trim_start")
    trim_end = data.get("trim_end")
    translate_subs = data.get("translate_subs")
    
    subtitle_lang = data.get("subtitle_lang")
    subtitle_mode = data.get("subtitle_mode") or "none"
    subtitle_translate = data.get("subtitle_translate") or "none"
    subtitle_url = data.get("subtitle_url")
    subtitle_content = data.get("subtitle_content")
    
    sub_font = data.get("sub_font") or "Arial"
    try:
        sub_size = float(data.get("sub_size") or 1.4)
    except:
        sub_size = 1.4
    sub_color = data.get("sub_color") or "#ffffff"
    sub_bg_color = data.get("sub_bg_color") or "#000000"
    try:
        sub_bg_opacity = int(data.get("sub_bg_opacity") or 50)
    except:
        sub_bg_opacity = 50
    try:
        sub_outline = int(data.get("sub_outline") or 2)
    except:
        sub_outline = 2
    sub_outline_color = data.get("sub_outline_color") or "#000000"
    sub_pos = data.get("sub_pos") or "bottom"
    
    export_type = data.get("export_type") or "default"
    if export_type == "gif":
        ext = "gif"
        
    color_filter = data.get("color_filter") or "none"
    enhance_beautify = bool(data.get("enhance_beautify"))
    try:
        enhance_sharpen = int(data.get("enhance_sharpen") or 0)
    except:
        enhance_sharpen = 0
    enhance_upscale = data.get("enhance_upscale") or "none"

    voiceover_active = bool(data.get("voiceover_active"))
    voiceover_voice = data.get("voiceover_voice") or "vi-VN-HoaiMyNeural"
    voiceover_rate = data.get("voiceover_rate")
    voiceover_pitch = data.get("voiceover_pitch")
    cloud_destination = data.get("cloud_destination") or "local"
    tg_bot_token = data.get("tg_bot_token")
    tg_chat_id = data.get("tg_chat_id")

    audio_eq_bass = data.get("audio_eq_bass") or 0
    audio_eq_lowmid = data.get("audio_eq_lowmid") or 0
    audio_eq_highmid = data.get("audio_eq_highmid") or 0
    audio_eq_treble = data.get("audio_eq_treble") or 0
    audio_speed = data.get("audio_speed") or 1.0
    audio_voice_preset = data.get("audio_voice_preset") or "normal"

    if not url or not format_id:
        return jsonify({"status": "error", "message": "URL and format_id are required."}), 400

    download_id = str(uuid.uuid4())
    current_user = get_authenticated_user()
    user_id = current_user["id"] if current_user else None

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
            "url": url,
            "format_id": format_id,
            "quality": quality,
            "title": title,
            "thumbnail": thumbnail,
            "user_id": user_id,
            "voiceover_active": voiceover_active,
            "voiceover_voice": voiceover_voice,
            "voiceover_rate": voiceover_rate,
            "voiceover_pitch": voiceover_pitch,
            "trim_start": trim_start,
            "trim_end": trim_end,
            "cloud_destination": cloud_destination,
            "audio_eq_bass": audio_eq_bass,
            "audio_eq_lowmid": audio_eq_lowmid,
            "audio_eq_highmid": audio_eq_highmid,
            "audio_eq_treble": audio_eq_treble,
            "audio_speed": audio_speed,
            "audio_voice_preset": audio_voice_preset,
            "subtitle_lang": subtitle_lang,
            "subtitle_mode": subtitle_mode,
            "subtitle_translate": subtitle_translate,
            "subtitle_url": subtitle_url,
            "subtitle_content": subtitle_content,
            "sub_font": sub_font,
            "sub_size": sub_size,
            "sub_color": sub_color,
            "sub_bg_color": sub_bg_color,
            "sub_bg_opacity": sub_bg_opacity,
            "sub_outline": sub_outline,
            "sub_outline_color": sub_outline_color,
            "sub_pos": sub_pos,
            "enhance_beautify": enhance_beautify,
            "enhance_sharpen": enhance_sharpen,
            "enhance_upscale": enhance_upscale,
            "color_filter": color_filter,
            "export_type": export_type,
            "timestamp": time.time(),
        }

    logger.info(f"Enqueued task {download_id} for {url} (client_id: {client_id})")
    thread = threading.Thread(
        target=bg_download_task, 
        args=(download_id, url, format_id, ext, quality, title, client_id),
        kwargs={
            "trim_start": trim_start, 
            "trim_end": trim_end, 
            "translate_subs": translate_subs,
            "export_type": export_type,
            "color_filter": color_filter,
            "enhance_beautify": enhance_beautify,
            "enhance_sharpen": enhance_sharpen,
            "enhance_upscale": enhance_upscale,
            "voiceover_active": voiceover_active,
            "voiceover_voice": voiceover_voice,
            "voiceover_rate": voiceover_rate,
            "voiceover_pitch": voiceover_pitch,
            "cloud_destination": cloud_destination,
            "tg_bot_token": tg_bot_token,
            "tg_chat_id": tg_chat_id,
            "episode": episode,
            "server": server,
            "audio_eq_bass": audio_eq_bass,
            "audio_eq_lowmid": audio_eq_lowmid,
            "audio_eq_highmid": audio_eq_highmid,
            "audio_eq_treble": audio_eq_treble,
            "audio_speed": audio_speed,
            "audio_voice_preset": audio_voice_preset,
            "subtitle_lang": subtitle_lang,
            "subtitle_mode": subtitle_mode,
            "subtitle_translate": subtitle_translate,
            "subtitle_url": subtitle_url,
            "subtitle_content": subtitle_content,
            "sub_font": sub_font,
            "sub_size": sub_size,
            "sub_color": sub_color,
            "sub_bg_color": sub_bg_color,
            "sub_bg_opacity": sub_bg_opacity,
            "sub_outline": sub_outline,
            "sub_outline_color": sub_outline_color,
            "sub_pos": sub_pos,
        }
    )
    thread.start()

    return jsonify({"status": "success", "download_id": download_id})


@download_bp.route("/api/download/history", methods=["GET"])
def get_download_history_api():
    current_user = get_authenticated_user()
    user_id = current_user["id"] if current_user else None
    history = downloads_status.get_history(limit=50, user_id=user_id)
    return jsonify({
        "status": "success",
        "history": history,
        "is_authenticated": bool(current_user),
        "user": current_user
    })


@download_bp.route("/api/download/history/clear", methods=["POST"])
def clear_download_history_api():
    current_user = get_authenticated_user()
    user_id = current_user["id"] if current_user else None
    success = downloads_status.clear_history(user_id=user_id)
    if success:
        return jsonify({"status": "success", "message": "Download history cleared."})
    else:
        return jsonify({"status": "error", "message": "Failed to clear download history."}), 500


@download_bp.route("/api/download/status/<download_id>", methods=["GET"])
def get_download_status(download_id):
    with downloads_status_lock:
        status_info = downloads_status.get(download_id)
    if not status_info:
        return jsonify({"status": "error", "message": "Download task not found."}), 404
    allowed, err_resp = check_task_ownership(status_info)
    if not allowed:
        return err_resp
    # Return a safe copy without internal paths
    return jsonify({
        "status": status_info["status"],
        "progress": status_info["progress"],
        "message": status_info["message"],
        "ext": status_info.get("ext", ""),
        "error": status_info.get("error"),
        "speed": status_info.get("speed", ""),
        "eta": status_info.get("eta", ""),
        "filename": status_info.get("filename", "")
    })


@download_bp.route("/api/download/progress/<download_id>", methods=["GET"])
def get_download_progress_sse(download_id):
    with downloads_status_lock:
        status_info = downloads_status.get(download_id)
        if status_info:
            allowed, err_resp = check_task_ownership(status_info)
            if not allowed:
                return err_resp

    def event_generator():
        last_progress = -1
        last_status = None
        consecutive_idle = 0
        try:
            while True:
                with downloads_status_lock:
                    status_info = downloads_status.get(download_id)
                
                if not status_info:
                    err_data = {"status": "error", "message": "Download task not found.", "progress": 0}
                    yield f"data: {json.dumps(err_data)}\n\n"
                    break
                
                cur_status = status_info.get("status")
                cur_progress = status_info.get("progress", 0)

                # Formulate update data
                data = {
                    "status": cur_status,
                    "progress": cur_progress,
                    "message": status_info.get("message", ""),
                    "ext": status_info.get("ext", ""),
                    "error": status_info.get("error"),
                    "speed": status_info.get("speed", ""),
                    "eta": status_info.get("eta", ""),
                }
                
                yield f"data: {json.dumps(data)}\n\n"
                
                # Check for termination conditions
                if cur_status in ["complete", "error", "cancelled"]:
                    break

                # Safety idle cutoff: if task is completely unchanged for 10 minutes (1200 ticks), stop thread
                if cur_status == last_status and cur_progress == last_progress:
                    consecutive_idle += 1
                    if consecutive_idle > 1200:
                        break
                else:
                    consecutive_idle = 0
                    last_status = cur_status
                    last_progress = cur_progress

                time.sleep(0.5)
        except (GeneratorExit, ConnectionResetError, BrokenPipeError):
            logger.info(f"SSE client disconnected for {download_id}")
        except Exception as e:
            logger.warning(f"SSE stream error for {download_id}: {e}")
            
    response = Response(event_generator(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@download_bp.route("/api/download/cancel/<download_id>", methods=["POST"])
def cancel_download(download_id):
    with downloads_status_lock:
        status_info = downloads_status.get(download_id)
        if not status_info:
            return jsonify({"status": "error", "message": "Download task not found."}), 404
        allowed, err_resp = check_task_ownership(status_info)
        if not allowed:
            return err_resp
        
        # Protect finished tasks
        if status_info.get("status") in ["complete", "error"]:
            return jsonify({"status": "success", "message": "Task already finished, ignoring cancellation."})
            
        # Mark as cancelled
        status_info["status"] = "cancelled"
        status_info["message"] = "Download cancelled by user."
        
    logger.info(f"Task {download_id} marked as cancelled by client.")
    return jsonify({"status": "success", "message": "Cancellation request submitted."})


@download_bp.route("/api/download/save-to-disk", methods=["POST"])
def save_download_to_disk():
    data = request.get_json(silent=True) or {}
    download_id = data.get("download_id")
    target_path = data.get("target_path")
    if not download_id or not target_path:
        return jsonify({"status": "error", "message": "Missing download_id or target_path"}), 400

    with downloads_status_lock:
        status_info = downloads_status.get(download_id)

    if not status_info or status_info.get("status") != "complete":
        return jsonify({"status": "error", "message": "File is not ready yet."}), 400

    allowed, err_resp = check_task_ownership(status_info)
    if not allowed:
        return err_resp

    src_path = status_info.get("filepath")
    if not src_path or not os.path.exists(src_path):
        return jsonify({"status": "error", "message": "Source file not found on disk."}), 404

    try:
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        shutil.copy2(src_path, target_path)
        logger.info(f"Direct disk save complete: {src_path} -> {target_path}")
        return jsonify({"status": "success", "saved_path": target_path})
    except Exception as e:
        logger.error(f"Failed to copy file to disk: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@download_bp.route("/api/download/open-folder", methods=["GET", "POST"])
def open_downloads_folder_endpoint():
    """Opens the local downloads directory on the host system, or returns web instructions if remote/cloud."""
    try:
        is_cloud = os.path.exists('/.dockerenv') or os.environ.get('RENDER') == 'true'
        client_ip = request.remote_addr or ""
        is_remote = client_ip not in ("127.0.0.1", "localhost", "::1", "testclient")

        if is_cloud or is_remote:
            return jsonify({
                "status": "notice",
                "mode": "web",
                "message": "Trình duyệt web không thể mở trực tiếp Explorer do bảo mật sandbox. File tải về nằm trong thư mục Downloads của máy bạn (bấm Ctrl+J để mở)."
            })

        folder = os.path.abspath(TEMP_DOWNLOAD_DIR)
        os.makedirs(folder, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            try:
                subprocess.Popen(["xdg-open", folder])
            except Exception:
                return jsonify({
                    "status": "notice",
                    "mode": "web",
                    "message": "Trình duyệt web không thể mở trực tiếp Explorer do bảo mật sandbox. File tải về nằm trong thư mục Downloads của máy bạn (bấm Ctrl+J để mở)."
                })
        return jsonify({"status": "success", "folder": folder})
    except Exception as e:
        logger.warning(f"Notice on open downloads folder: {e}")
        return jsonify({
            "status": "notice",
            "mode": "web",
            "message": "File tải về nằm trong thư mục Downloads của máy bạn (bấm Ctrl+J để mở)."
        }), 200


@download_bp.route("/api/download/open-file", methods=["POST"])
def open_download_file_endpoint():
    """Opens a downloaded or converted file using the system default player/app."""
    data = request.get_json(silent=True) or {}
    download_id = data.get("download_id")
    file_path = data.get("file_path")
    target = None

    if file_path and os.path.exists(file_path):
        target = file_path
    elif download_id:
        with downloads_status_lock:
            status_info = downloads_status.get(download_id)
        if status_info and status_info.get("filepath") and os.path.exists(status_info.get("filepath")):
            target = status_info.get("filepath")

    if not target:
        return jsonify({"status": "error", "message": "File not found on system."}), 404

    from utils.security import is_safe_local_media_path
    safe, reason = is_safe_local_media_path(target, allow_user_local_media=True)
    if not safe:
        logger.warning(f"Blocked open_file attempt for unsafe target '{target}': {reason}")
        return jsonify({"status": "error", "message": f"Security restriction: {reason}"}), 403

    try:
        abs_target = os.path.abspath(target)
        if sys.platform.startswith("win"):
            os.startfile(abs_target)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", abs_target])
        else:
            subprocess.Popen(["xdg-open", abs_target])
        return jsonify({"status": "success", "file": abs_target})
    except Exception as e:
        logger.error(f"Failed to open file {target}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@download_bp.route("/api/download/file/<download_id>", methods=["GET"])
def get_download_file(download_id):
    with downloads_status_lock:
        status_info = downloads_status.get(download_id)

    if not status_info:
        return """
        <html>
            <head>
                <title>File Purged | Meikova Harvest</title>
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

    allowed, err_resp = check_task_ownership(status_info)
    if not allowed:
        return err_resp

    if status_info["status"] != "complete":
        return """
        <html>
            <head>
                <title>File Purged | Meikova Harvest</title>
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
    filename = status_info["filename"]
    ext = filepath.rsplit(".", 1)[-1] if "." in filepath else "mp4"

    if not os.path.exists(filepath):
        return jsonify({"status": "error", "message": "File not found on server."}), 404

    import mimetypes
    mime_overrides = {
        "mp3": "audio/mpeg",
        "m4a": "audio/mp4",
        "wav": "audio/wav",
        "flac": "audio/flac",
        "ogg": "audio/ogg",
        "oga": "audio/ogg",
        "opus": "audio/opus",
        "mp4": "video/mp4",
        "mkv": "video/x-matroska",
        "webm": "video/webm",
        "mov": "video/quicktime",
        "avi": "video/x-msvideo",
        "ts": "video/mp2t",
        "gif": "image/gif",
        "webp": "image/webp",
        "vtt": "text/vtt",
        "html": "text/html; charset=utf-8",
        "htm": "text/html; charset=utf-8",
        "txt": "text/plain; charset=utf-8",
        "srt": "text/plain; charset=utf-8",
        "json": "application/json"
    }
    content_type = mime_overrides.get(ext.lower())
    if not content_type:
        guessed_type, _ = mimetypes.guess_type(filepath)
        content_type = guessed_type or "application/octet-stream"

    preview_mode = request.args.get("preview", "false").lower() == "true"

    resp = send_file(
        filepath,
        mimetype=content_type,
        as_attachment=not preview_mode,
        download_name=filename,
        conditional=True
    )
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp



def apply_image_effects(image_bytes, brightness=100.0, contrast=100.0, saturation=100.0, hue=0.0, exposure=100.0, blur=0.0, grayscale=0.0, sepia=0.0, invert=0.0):
    from PIL import Image, ImageEnhance, ImageOps, ImageFilter
    import io

    img = Image.open(io.BytesIO(image_bytes))

    # Convert to RGB or RGBA depending on mode
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        has_alpha = True
    else:
        img = img.convert("RGB")
        has_alpha = False

    # Apply Brightness
    if brightness != 100.0:
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness / 100.0)

    # Apply Exposure (another pass of brightness)
    if exposure != 100.0:
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(exposure / 100.0)

    # Apply Contrast
    if contrast != 100.0:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast / 100.0)

    # Apply Saturation
    if saturation != 100.0:
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(saturation / 100.0)

    # Apply Hue Rotate
    if hue != 0.0:
        if has_alpha:
            alpha = img.split()[-1]
            rgb_img = img.convert("RGB")
        else:
            rgb_img = img
        
        hsv_img = rgb_img.convert("HSV")
        h, s, v = hsv_img.split()
        shift = int(hue * 255.0 / 360.0)
        h = h.point(lambda x: (x + shift) % 256)
        rotated_rgb = Image.merge("HSV", (h, s, v)).convert("RGB")
        
        if has_alpha:
            img = Image.merge("RGBA", (*rotated_rgb.split(), alpha))
        else:
            img = rotated_rgb

    # Apply Grayscale
    if grayscale > 0.0:
        if has_alpha:
            alpha = img.split()[-1]
            rgb_img = img.convert("RGB")
            gray_img = rgb_img.convert("L").convert("RGB")
            blended_rgb = Image.blend(rgb_img, gray_img, grayscale / 100.0)
            img = Image.merge("RGBA", (*blended_rgb.split(), alpha))
        else:
            gray_img = img.convert("L").convert("RGB")
            img = Image.blend(img, gray_img, grayscale / 100.0)

    # Apply Sepia
    if sepia > 0.0:
        sepia_matrix = (
            0.393, 0.769, 0.189, 0,
            0.349, 0.686, 0.168, 0,
            0.272, 0.534, 0.131, 0
        )
        if has_alpha:
            alpha = img.split()[-1]
            rgb_img = img.convert("RGB")
            sepia_img = rgb_img.convert("RGB", sepia_matrix)
            blended_rgb = Image.blend(rgb_img, sepia_img, sepia / 100.0)
            img = Image.merge("RGBA", (*blended_rgb.split(), alpha))
        else:
            sepia_img = img.convert("RGB", sepia_matrix)
            img = Image.blend(img, sepia_img, sepia / 100.0)

    # Apply Invert
    if invert > 0.0:
        if has_alpha:
            alpha = img.split()[-1]
            rgb_img = img.convert("RGB")
            inv_img = ImageOps.invert(rgb_img)
            blended_rgb = Image.blend(rgb_img, inv_img, invert / 100.0)
            img = Image.merge("RGBA", (*blended_rgb.split(), alpha))
        else:
            inv_img = ImageOps.invert(img)
            img = Image.blend(img, inv_img, invert / 100.0)

    # Apply Blur
    if blur > 0.0:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur))

    out_io = io.BytesIO()
    img.save(out_io, format="PNG" if has_alpha else "JPEG")
    return out_io.getvalue()


@download_bp.route("/api/download/image", methods=["GET"])
def download_image():
    url = request.args.get("url")
    filename = request.args.get("filename") or "image.jpg"
    client_id = request.args.get("client_id")
    if not url:
        return "Missing url parameter", 400

    from utils.security import is_safe_remote_url
    safe, reason = is_safe_remote_url(url)
    if not safe:
        logger.warning(f"Blocked download_image SSRF attempt for '{url}': {reason}")
        return f"Security restriction: {reason}", 403

    # Parse Image Filter Parameters
    try:
        brightness = float(request.args.get("brightness", "100"))
        contrast = float(request.args.get("contrast", "100"))
        saturation = float(request.args.get("saturation", "100"))
        hue = float(request.args.get("hue", "0"))
        exposure = float(request.args.get("exposure", "100"))
        blur = float(request.args.get("blur", "0"))
        grayscale = float(request.args.get("grayscale", "0"))
        sepia = float(request.args.get("sepia", "0"))
        invert = float(request.args.get("invert", "0"))
    except ValueError:
        brightness = contrast = saturation = exposure = 100.0
        hue = blur = grayscale = sepia = invert = 0.0

    has_image_filters = (
        brightness != 100.0 or
        contrast != 100.0 or
        saturation != 100.0 or
        hue != 0.0 or
        exposure != 100.0 or
        blur != 0.0 or
        grayscale != 0.0 or
        sepia != 0.0 or
        invert != 0.0
    )

    try:
        headers = {
            "User-Agent": DEFAULT_MEDIA_USER_AGENT,
            "Referer": get_referer_by_url(url)
        }
        
        cookies_dict = {}
        client_cookies = get_cookie_file_path(client_id)
        if client_cookies and os.path.exists(client_cookies):
            try:
                with open(client_cookies, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        parts = line.split('\t')
                        if len(parts) >= 7:
                            cookies_dict[parts[5]] = parts[6]
            except Exception as cookie_err:
                logger.warning(f"Failed to parse cookies file {client_cookies}: {cookie_err}")

        resp = requests.get(url, headers=headers, cookies=cookies_dict, stream=True, timeout=15)
        if resp.status_code == 200:
            content_data = resp.content
            if has_image_filters:
                try:
                    content_data = apply_image_effects(
                        content_data,
                        brightness=brightness,
                        contrast=contrast,
                        saturation=saturation,
                        hue=hue,
                        exposure=exposure,
                        blur=blur,
                        grayscale=grayscale,
                        sepia=sepia,
                        invert=invert
                    )
                except Exception as img_err:
                    logger.error(f"Failed to apply image filters: {img_err}")

            fallback_filename = "image.jpg"
            encoded_filename = quote(filename)
            resp_headers = {
                "Content-Disposition": f'attachment; filename="{fallback_filename}"; filename*=UTF-8\'\'{encoded_filename}',
                "Content-Type": "image/png" if (has_image_filters and ("transparency" in resp.headers.get("Content-Type", "").lower() or "png" in resp.headers.get("Content-Type", "").lower())) else resp.headers.get("Content-Type", "image/jpeg")
            }
            return Response(content_data, headers=resp_headers)
        else:
            return f"Failed to download image: HTTP {resp.status_code}", 500
    except Exception as e:
        return f"Error: {e}", 500


@download_bp.route("/api/proxy/image", methods=["GET"])
def proxy_image():
    url = request.args.get("url")
    client_id = request.args.get("client_id")
    if not url:
        return "Missing url parameter", 400

    from utils.security import is_safe_local_media_path, is_safe_remote_url

    # Serve local image file directly
    if (os.path.isabs(url) or (len(url) >= 2 and url[1] == ':')) and os.path.exists(url):
        safe, reason = is_safe_local_media_path(url, allow_user_local_media=True)
        if not safe:
            logger.warning(f"Blocked proxy_image local access to '{url}': {reason}")
            return jsonify({"status": "error", "message": f"Security restriction: {reason}", "code": "ACCESS_DENIED"}), 403
        try:
            ext = url.rsplit('.', 1)[-1].lower() if '.' in url else ''
            
            if ext in ['heic', 'heif']:
                try:
                    from PIL import Image
                    import io
                    from pillow_heif import register_heif_opener
                    register_heif_opener()
                    
                    image = Image.open(url)
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    
                    img_io = io.BytesIO()
                    image.save(img_io, 'JPEG', quality=85)
                    img_io.seek(0)
                    return send_file(img_io, mimetype='image/jpeg', conditional=True)
                except Exception as convert_err:
                    logger.error(f"Failed to convert HEIC image {url}: {convert_err}")
                    return f"HEIC conversion failed: {convert_err}", 500

            mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif', 'webp': 'image/webp', 'bmp': 'image/bmp', 'svg': 'image/svg+xml', 'ico': 'image/x-icon', 'heic': 'image/heic', 'heif': 'image/heif', 'tiff': 'image/tiff', 'tif': 'image/tiff', 'avif': 'image/avif'}
            mimetype = mime_map.get(ext, 'application/octet-stream')
            return send_file(url, mimetype=mimetype, conditional=True)
        except Exception as e:
            return f"Error serving local image: {e}", 500

    # Remote URL SSRF defense
    safe, reason = is_safe_remote_url(url)
    if not safe:
        logger.warning(f"Blocked proxy_image remote SSRF attempt to '{url}': {reason}")
        return jsonify({"status": "error", "message": f"Security restriction: {reason}", "code": "ACCESS_DENIED"}), 403

    try:
        headers = {
            "User-Agent": DEFAULT_MEDIA_USER_AGENT,
            "Referer": get_referer_by_url(url)
        }
        
        cookies_dict = {}
        client_cookies = get_cookie_file_path(client_id)
        if client_cookies and os.path.exists(client_cookies):
            try:
                with open(client_cookies, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        parts = line.split('\t')
                        if len(parts) >= 7:
                            cookies_dict[parts[5]] = parts[6]
            except Exception as cookie_err:
                logger.warning(f"Failed to parse cookies file {client_cookies}: {cookie_err}")

        resp = requests.get(url, headers=headers, cookies=cookies_dict, timeout=15)
        if resp.status_code == 200:
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            # Detect anti-bot block pages: CDN returns HTML instead of image
            if content_type.startswith("text/html") or (resp.content[:50].strip().startswith(b"<") and not content_type.startswith("image/")):
                logger.warning(f"Proxy image blocked by CDN (HTML response): {url[:120]}")
                return Response(FALLBACK_IMAGE_PLACEHOLDER_SVG, mimetype="image/svg+xml")
            if not content_type.startswith("image/"):
                content_type = "image/jpeg"
            return Response(resp.content, mimetype=content_type)
        else:
            logger.info(f"Upstream image returned HTTP {resp.status_code} ({url[:100]}...). Serving fallback image.")
            return Response(FALLBACK_IMAGE_PLACEHOLDER_SVG, mimetype="image/svg+xml")
    except Exception as e:
        logger.info(f"Failed to fetch proxy image {url[:100]}: {e}. Serving fallback image.")
        return Response(FALLBACK_IMAGE_PLACEHOLDER_SVG, mimetype="image/svg+xml")


@download_bp.route("/api/download/images/zip", methods=["POST"])
def download_images_zip():
    data = request.get_json(silent=True) or {}
    urls = data.get("urls", [])
    title = data.get("title", "images")
    client_id = data.get("client_id")
    if not urls:
        return jsonify({"status": "error", "message": "No urls provided"}), 400
    if len(urls) > 100:
        return jsonify({"status": "error", "message": "Too many URLs in request (max 100)", "code": "LIMIT_EXCEEDED"}), 400

    from utils.security import is_safe_remote_url
    from flask import after_this_request
    import tempfile

    try:
        cookies_dict = {}
        client_cookies = get_cookie_file_path(client_id)
        if client_cookies and os.path.exists(client_cookies):
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
                except Exception as cookie_err:
                    logger.warning(f"Failed to parse cookies file {client_cookies}: {cookie_err}")
        
        tmp_zip = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        tmp_zip_path = tmp_zip.name
        tmp_zip.close()

        @after_this_request
        def remove_temp_zip(response):
            try:
                if os.path.exists(tmp_zip_path):
                    os.remove(tmp_zip_path)
            except Exception:
                pass
            return response

        with zipfile.ZipFile(tmp_zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            for idx, item in enumerate(urls):
                url = item.get("url")
                label = item.get("label", f"image_{idx+1}")
                ext = item.get("ext", "jpg")
                if not url:
                    continue
                safe, _ = is_safe_remote_url(url)
                if not safe:
                    logger.warning(f"Blocked prohibited remote URL in images zip: {url}")
                    continue
                try:
                    req_headers = headers.copy()
                    req_headers["Referer"] = get_referer_by_url(url)
                    resp = requests.get(url, headers=req_headers, cookies=cookies_dict, timeout=10)
                    if resp.status_code == 200:
                        safe_label = re.sub(r'[\\/*?:"<>|]', "", label).strip()
                        filename = f"{safe_label}.{ext}"
                        zf.writestr(filename, resp.content)
                except Exception as e:
                    logger.warning(f"Failed to zip image {url}: {e}")
                    
        return send_file(
            tmp_zip_path,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{title}_images.zip"
        )
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to create ZIP: {e}"}), 500


@download_bp.route("/api/proxy/stream")
def proxy_stream():
    url = request.args.get("url")
    if not url:
        return "Missing url parameter", 400
    from utils.security import is_safe_local_media_path, is_safe_remote_url

    # Serve local media file directly
    if os.path.isabs(url) and os.path.isfile(url):
        safe, reason = is_safe_local_media_path(url, allow_user_local_media=True)
        if not safe:
            logger.warning(f"Blocked proxy_stream local access to '{url}': {reason}")
            return f"Security restriction: {reason}", 403
        try:
            ext = url.rsplit('.', 1)[-1].lower() if '.' in url else ''
            mime_map = {
                'mp4': 'video/mp4', 'mkv': 'video/x-matroska', 'avi': 'video/x-msvideo',
                'mov': 'video/quicktime', 'webm': 'video/webm', 'flv': 'video/x-flv',
                'ts': 'video/mp2t', 'mpg': 'video/mpeg', 'mpeg': 'video/mpeg', 'm4v': 'video/mp4',
                'mp3': 'audio/mpeg', 'm4a': 'audio/mp4', 'wav': 'audio/wav',
                'flac': 'audio/flac', 'ogg': 'audio/ogg', 'aac': 'audio/aac',
                'wma': 'audio/x-ms-wma', 'opus': 'audio/opus',
                'txt': 'text/plain', 'xml': 'application/xml', 'json': 'application/json',
                'csv': 'text/csv', 'html': 'text/html', 'htm': 'text/html'
            }
            mimetype = mime_map.get(ext, 'application/octet-stream')
            return send_file(url, mimetype=mimetype, conditional=True)
        except Exception as e:
            return f"Error serving local file: {e}", 500

    # Remote URL SSRF defense
    safe, reason = is_safe_remote_url(url)
    if not safe:
        logger.warning(f"Blocked proxy_stream remote SSRF attempt to '{url}': {reason}")
        return f"Security restriction: {reason}", 403

    client_id = request.args.get("client_id")
    referer = get_referer_by_url(url)
    headers = {
        "User-Agent": DEFAULT_MEDIA_USER_AGENT
    }
    if referer:
        headers["Referer"] = referer
        
    # Forward Range headers to support partial content requests
    range_header = request.headers.get("Range")
    if range_header:
        headers["Range"] = range_header
        
    cookies_dict = {}
    client_cookies = get_cookie_file_path(client_id)
    if client_cookies and os.path.exists(client_cookies):
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
            except Exception as cookie_err:
                logger.warning(f"Failed to parse cookies for proxy stream: {cookie_err}")
                
    resp = None
    try:
        from curl_cffi import requests as curl_requests
        resp = curl_requests.get(url, headers=headers, cookies=cookies_dict, stream=True, verify=False, impersonate="chrome", timeout=12)
    except Exception as curl_err:
        logger.warning(f"curl_cffi proxy stream failed for {url}: {curl_err}. Falling back to standard requests with DoH...")
        try:
            import requests as std_requests
            resp = std_requests.get(url, headers=headers, cookies=cookies_dict, stream=True, verify=False, timeout=12)
        except Exception as req_err:
            logger.error(f"Fallback requests also failed for proxy stream: {req_err}")
            return f"Proxy error: {req_err}", 500

    try:
        content_type = resp.headers.get("Content-Type", "")
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        url_path = parsed_url.path.lower()
        url_query = parsed_url.query.lower()
        
        is_hls_by_url = (
            (".m3u8" in url_path or ".m3u8" in url_query or 
             "mpegurl" in content_type.lower() or 
             "application/vnd.apple.mpegurl" in content_type.lower())
            and not (url_path.endswith(".ts") or "seg.ts" in url_path)
        )
                         
        first_chunk = next(resp.iter_content(chunk_size=1024), b"")
        cleaned_start = first_chunk.lstrip(b"\xef\xbb\xbf\r\n\t ")
        is_hls = (
            is_hls_by_url or cleaned_start.startswith(b"#EXTM3U")
        ) and cleaned_start.startswith(b"#EXTM3U")
                  
        if is_hls:
            chunks = [first_chunk]
            for chunk in resp.iter_content(chunk_size=65536):
                chunks.append(chunk)
            manifest_text = b"".join(chunks).decode("utf-8", errors="ignore")
            from urllib.parse import urljoin
            lines = []
            for line in manifest_text.splitlines():
                line = line.strip()
                if not line:
                    lines.append("")
                    continue
                if line.startswith("#"):
                    # Rewrite encryption key URIs if present so the browser player can fetch the decryption keys through our proxy
                    if line.startswith("#EXT-X-KEY:") or line.startswith("#EXT-X-SESSION-KEY:"):
                        uri_match = re.search(r'URI="([^"]+)"', line)
                        if uri_match:
                            original_uri = uri_match.group(1)
                            abs_uri = urljoin(url, original_uri)
                            client_suffix = f"&client_id={quote(client_id)}" if client_id else ""
                            proxy_uri = f"/api/proxy/stream?url={quote(abs_uri)}{client_suffix}"
                            line = line.replace(f'URI="{original_uri}"', f'URI="{proxy_uri}"')
                    lines.append(line)
                else:
                    absolute_url = urljoin(url, line)
                    client_suffix = f"&client_id={quote(client_id)}" if client_id else ""
                    lines.append(f"/api/proxy/stream?url={quote(absolute_url)}{client_suffix}")
                    
            resp_headers = {
                "Content-Type": "application/x-mpegURL",
                "Access-Control-Allow-Origin": "*"
            }
            return "\n".join(lines), 200, resp_headers
            
        # Determine appropriate Content-Type for binary video/audio streams
        detected_ct = content_type
        if not detected_ct or detected_ct in ["application/octet-stream", "text/plain"]:
            if url_path.endswith(".mp3") or ".mp3" in url_query:
                detected_ct = "audio/mpeg"
            elif url_path.endswith(".m4a") or ".m4a" in url_query:
                detected_ct = "audio/mp4"
            elif url_path.endswith(".ogg") or url_path.endswith(".opus"):
                detected_ct = "audio/ogg"
            elif url_path.endswith(".wav"):
                detected_ct = "audio/wav"
            elif url_path.endswith(".flac"):
                detected_ct = "audio/flac"
            elif url_path.endswith(".webm") or ".webm" in url_query:
                detected_ct = "video/webm"
            else:
                detected_ct = "video/mp4"

        # For HLS segments or binary video streams
        def generate():
            try:
                if first_chunk:
                    yield first_chunk
                for chunk in resp.iter_content(chunk_size=65536):
                    yield chunk
            except Exception as stream_err:
                logger.warning(f"Error streaming content: {stream_err}")
                
        resp_headers = {
            "Content-Type": detected_ct,
            "Access-Control-Allow-Origin": "*",
            "Accept-Ranges": "bytes"
        }
        
        # Forward range-request specific headers
        for h in ["Content-Range", "Accept-Ranges", "Content-Length"]:
            if h in resp.headers:
                resp_headers[h] = resp.headers[h]
                
        return Response(generate(), status=resp.status_code, headers=resp_headers, direct_passthrough=True)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Proxy error: {e}", 500


@download_bp.route("/api/download/history/delete/<download_id>", methods=["POST"])
def delete_download_history_item(download_id):
    data = request.get_json(silent=True) or {}
    delete_file = bool(data.get("delete_file", False))
    
    with downloads_status_lock:
        status_info = downloads_status.get(download_id)
        
    if not status_info:
        return jsonify({"status": "error", "message": "Download task not found."}), 404

    allowed, err_resp = check_task_ownership(status_info)
    if not allowed:
        return err_resp
        
    if delete_file:
        filepath = status_info.get("filepath")
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info(f"Deleted physical file: {filepath}")
            except Exception as e:
                logger.warning(f"Failed to delete physical file {filepath}: {e}")
                
        temp_dir = status_info.get("temp_dir")
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Deleted temp directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to delete temp directory {temp_dir}: {e}")

    success = downloads_status.delete_task(download_id)
    if success:
        return jsonify({"status": "success", "message": "Download task deleted."})
    else:
        return jsonify({"status": "error", "message": "Failed to delete task from database."}), 500


@download_bp.route("/api/proxy/stream_adaptive")
def proxy_stream_adaptive():
    import subprocess
    video_url = request.args.get("video_url")
    audio_url = request.args.get("audio_url", "")
    if not video_url:
        return "Missing video_url parameter", 400

    start_time = request.args.get("start_time", "0")
    try:
        start_time_sec = float(start_time)
        if start_time_sec < 0:
            start_time_sec = 0.0
    except ValueError:
        start_time_sec = 0.0

    start_time_str = f"{start_time_sec:.3f}"
    container = request.args.get("container", "mp4").lower()
    
    if container in ["webm", "mkv"]:
        fmt_flag = "webm"
        movflags = []
        mimetype = "video/webm"
    else:
        fmt_flag = "mp4"
        movflags = ["-movflags", "frag_keyframe+empty_moov+default_base_moof"]
        mimetype = "video/mp4"

    client_id = request.args.get("client_id")
    headers_arg = f"User-Agent: {DEFAULT_MEDIA_USER_AGENT}\r\n"

    # Forward Referer header if available
    referer = get_referer_by_url(video_url)
    if referer:
        headers_arg += f"Referer: {referer}\r\n"

    # Load and forward client cookies
    cookies_str = ""
    client_cookies = get_cookie_file_path(client_id)
    if client_cookies and os.path.exists(client_cookies):
            try:
                cookies_list = []
                with open(client_cookies, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        parts = line.split('\t')
                        if len(parts) >= 7:
                            cookies_list.append(f"{parts[5]}={parts[6]}")
                if cookies_list:
                    cookies_str = "Cookie: " + "; ".join(cookies_list) + "\r\n"
            except Exception as cookie_err:
                logger.warning(f"Failed to load cookies for adaptive stream proxy: {cookie_err}")

    if cookies_str:
        headers_arg += cookies_str

    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except Exception as path_e:
        logger.warning(f"Failed to add static-ffmpeg paths: {path_e}")

    from utils.security import is_safe_remote_url, is_safe_local_media_path
    safe_v, reason_v = is_safe_remote_url(video_url) if (video_url.startswith("http://") or video_url.startswith("https://")) else is_safe_local_media_path(video_url, allow_user_local_media=True)
    if not safe_v:
        logger.warning(f"Blocked proxy_stream_adaptive video_url: {reason_v}")
        return jsonify({"status": "error", "message": f"Security restriction: {reason_v}", "code": "ACCESS_DENIED"}), 403

    if audio_url:
        safe_a, reason_a = is_safe_remote_url(audio_url) if (audio_url.startswith("http://") or audio_url.startswith("https://")) else is_safe_local_media_path(audio_url, allow_user_local_media=True)
        if not safe_a:
            logger.warning(f"Blocked proxy_stream_adaptive audio_url: {reason_a}")
            return jsonify({"status": "error", "message": f"Security restriction: {reason_a}", "code": "ACCESS_DENIED"}), 403

    # Build FFmpeg command to mux video-only and audio-only URLs on-the-fly
    cmd = [
        "ffmpeg",
        "-y",
        "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
        "-ss", start_time_str,
        "-headers", headers_arg,
        "-i", video_url,
    ]
    if audio_url:
        cmd.extend([
            "-ss", start_time_str,
            "-headers", headers_arg,
            "-i", audio_url,
            "-c:v", "copy",
            "-c:a", "copy",
        ])
    else:
        cmd.extend([
            "-c:v", "copy",
            "-an",
        ])
    cmd.extend(["-f", fmt_flag])
    if movflags:
        cmd.extend(movflags)
    cmd.append("pipe:1")

    logger.info(f"Spawning adaptive stream muxing (container={container}): {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=10 ** 6  # 1MB buffer
    )

    def generate():
        try:
            while True:
                chunk = process.stdout.read(65536)
                if not chunk:
                    break
                yield chunk
        except Exception as stream_err:
            logger.warning(f"Error streaming adaptive content: {stream_err}")
        finally:
            try:
                process.terminate()
                process.wait(timeout=2)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass

    resp_headers = {
        "Content-Type": mimetype,
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    }
    return Response(generate(), mimetype=mimetype, headers=resp_headers)


@download_bp.route("/api/media/play/<download_id>")
def play_media(download_id):
    # Fetch record from downloads_status
    with downloads_status_lock:
        task = downloads_status.get(download_id)
        
    if not task:
        # Fallback to sqlite manual fetch
        import sqlite3
        from utils.helpers import DB_PATH
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5.0)
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM downloads WHERE download_id = ?", (download_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                task = json.loads(row[0])
        except Exception:
            pass

    if not task:
        return jsonify({"status": "error", "message": "Media download not found."}), 404

    allowed, err_resp = check_task_ownership(task)
    if not allowed:
        return err_resp

    filepath = task.get("filepath")
    if not filepath or not os.path.exists(filepath):
        return jsonify({"status": "error", "message": "Offline media file not found on disk."}), 404

    # Stream file using Flask send_file with conditional=True to support Range seeking
    ext = filepath.rsplit('.', 1)[-1].lower() if '.' in filepath else ''
    mime_map = {
        'mp4': 'video/mp4', 'mkv': 'video/x-matroska', 'avi': 'video/x-msvideo',
        'mov': 'video/quicktime', 'webm': 'video/webm', 'flv': 'video/x-flv',
        'ts': 'video/mp2t', 'mpg': 'video/mpeg', 'mpeg': 'video/mpeg', 'm4v': 'video/mp4',
        'mp3': 'audio/mpeg', 'm4a': 'audio/mp4', 'wav': 'audio/wav',
        'flac': 'audio/flac', 'ogg': 'audio/ogg', 'aac': 'audio/aac',
        'wma': 'audio/x-ms-wma', 'opus': 'audio/opus',
        'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif'
    }
    mimetype = mime_map.get(ext, 'application/octet-stream')
    try:
        return send_file(filepath, mimetype=mimetype, conditional=True)
    except Exception as e:
        logger.error(f"Error serving media file: {e}")
        return jsonify({"status": "error", "message": f"Failed to stream media: {e}"}), 500


@download_bp.route("/api/media/telegram/<download_id>", methods=["POST"])
def send_media_to_telegram(download_id):
    data = request.get_json(silent=True) or {}
    bot_token = (data.get("tg_bot_token") or "").strip()
    chat_id = (data.get("tg_chat_id") or "").strip()

    if not bot_token or not chat_id:
        return jsonify({"status": "error", "message": "Missing Telegram Bot Token or Chat ID."}), 400

    with downloads_status_lock:
        task = downloads_status.get(download_id)

    if not task:
        import sqlite3
        from utils.helpers import DB_PATH
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5.0)
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM downloads WHERE download_id = ?", (download_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                task = json.loads(row[0])
        except Exception:
            pass

    if not task:
        return jsonify({"status": "error", "message": "Media download not found."}), 404

    allowed, err_resp = check_task_ownership(task)
    if not allowed:
        return err_resp

    filepath = task.get("filepath")
    if not filepath or not os.path.exists(filepath):
        return jsonify({"status": "error", "message": "Physical file not found on server disk."}), 404

    from tasks.download import upload_to_telegram
    success, msg = upload_to_telegram(filepath, bot_token, chat_id)
    if success:
        return jsonify({"status": "success", "message": "Uploaded successfully to Telegram cloud!"})
    else:
        return jsonify({"status": "error", "message": msg}), 500


# Cached release metadata with 10-minute TTL to prevent GitHub rate-limiting
_release_cache = {
    "timestamp": 0,
    "tag_name": "v2.0.7",
    "assets": []
}

VALID_APP_TARGETS = {
    "windows", "win", "win-setup", "exe",
    "win-portable", "portable",
    "msi",
    "macos", "mac", "dmg", "macos-arm64", "macos-x64", "mac-intel", "mac-zip", "darwin-zip",
    "linux", "appimage", "linux-appimage",
    "deb", "linux-deb",
    "tar", "linux-tar", "tar.gz",
    "extension", "chrome", "edge", "brave"
}

def get_latest_github_release_assets():
    """Lay danh sach tep dinh kem (assets) tu ban phat hanh GitHub moi nhat (TTL: 10 phut)."""
    global _release_cache
    now = time.time()
    if now - _release_cache["timestamp"] < 600 and _release_cache["assets"]:
        return _release_cache
    
    url = "https://api.github.com/repos/Meikova/meikova-harvest-tool/releases/latest"
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Meikova-Harvest-Server"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                tag_name = data.get("tag_name", "v2.0.7")
                assets = [
                    {"name": a.get("name", ""), "url": a.get("browser_download_url", "")}
                    for a in data.get("assets", [])
                ]
                if assets:
                    _release_cache = {
                        "timestamp": now,
                        "tag_name": tag_name,
                        "assets": assets
                    }
    except Exception as e:
        logger.warning(f"Failed to query GitHub release metadata: {e}")
    return _release_cache


def resolve_target_download_url(target_lower):
    """Phan giai muc tieu tai (target) thanh URL tai file chinh xac tu GitHub Release, triet tieu loi 404."""
    if target_lower not in VALID_APP_TARGETS:
        return None

    rel = get_latest_github_release_assets()
    assets = rel.get("assets", [])
    tag_name = rel.get("tag_name", "v2.0.7")
    
    # 1. Tim asset truc tiep tu GitHub Release thuc te
    for a in assets:
        name = a["name"].lower()
        url = a["url"]
        
        if target_lower in ("windows", "win", "win-setup", "exe"):
            if "setup" in name and name.endswith(".exe"):
                return url
        elif target_lower in ("win-portable", "portable"):
            if "portable" in name and name.endswith(".exe"):
                return url
        elif target_lower in ("msi",):
            if name.endswith(".msi"):
                return url
        elif target_lower in ("macos-x64", "mac-intel"):
            if "x64" in name and name.endswith(".dmg"):
                return url
        elif target_lower in ("macos", "mac", "dmg", "macos-arm64"):
            if "arm64" in name and name.endswith(".dmg"):
                return url
        elif target_lower in ("mac-zip", "darwin-zip"):
            if "zip" in name and ("mac" in name or "darwin" in name or "arm64" in name):
                return url
        elif target_lower in ("linux", "appimage", "linux-appimage"):
            if name.endswith(".appimage"):
                return url
        elif target_lower in ("deb", "linux-deb"):
            if name.endswith(".deb"):
                return url
        elif target_lower in ("tar", "linux-tar", "tar.gz"):
            if name.endswith(".tar.gz"):
                return url

    # Fallback chon .dmg bat ky neu macOS arm64 khong khop
    if target_lower in ("macos", "mac", "dmg", "macos-arm64"):
        for a in assets:
            if a["name"].lower().endswith(".dmg"):
                return a["url"]

    # 2. Fallback neu chua ket noi duoc GitHub API: Dung version dong tu tag_name
    clean_version = tag_name.lstrip("v")
    fallback_map = {
        "windows": f"MeikovaHarvest-Setup-{clean_version}.exe",
        "win": f"MeikovaHarvest-Setup-{clean_version}.exe",
        "win-setup": f"MeikovaHarvest-Setup-{clean_version}.exe",
        "exe": f"MeikovaHarvest-Setup-{clean_version}.exe",
        "win-portable": f"MeikovaHarvest-Portable-{clean_version}.exe",
        "portable": f"MeikovaHarvest-Portable-{clean_version}.exe",
        "msi": f"MeikovaHarvest-{clean_version}.msi",
        "macos": f"MeikovaHarvest-{clean_version}-arm64.dmg",
        "mac": f"MeikovaHarvest-{clean_version}-arm64.dmg",
        "dmg": f"MeikovaHarvest-{clean_version}-arm64.dmg",
        "macos-arm64": f"MeikovaHarvest-{clean_version}-arm64.dmg",
        "macos-x64": f"MeikovaHarvest-{clean_version}-x64.dmg",
        "mac-intel": f"MeikovaHarvest-{clean_version}-x64.dmg",
        "mac-zip": f"MeikovaHarvest-{clean_version}-arm64.zip",
        "darwin-zip": f"MeikovaHarvest-{clean_version}-arm64.zip",
        "linux": f"MeikovaHarvest-{clean_version}-x86_64.AppImage",
        "appimage": f"MeikovaHarvest-{clean_version}-x86_64.AppImage",
        "linux-appimage": f"MeikovaHarvest-{clean_version}-x86_64.AppImage",
        "deb": f"MeikovaHarvest-{clean_version}-amd64.deb",
        "linux-deb": f"MeikovaHarvest-{clean_version}-amd64.deb",
        "tar": f"MeikovaHarvest-{clean_version}-x64.tar.gz",
        "linux-tar": f"MeikovaHarvest-{clean_version}-x64.tar.gz",
        "tar.gz": f"MeikovaHarvest-{clean_version}-x64.tar.gz"
    }
    
    fallback_file = fallback_map.get(target_lower)
    if fallback_file:
        return f"https://github.com/Meikova/meikova-harvest-tool/releases/download/{tag_name}/{fallback_file}"
        
    return f"https://github.com/Meikova/meikova-harvest-tool/releases/tag/{tag_name}"


@download_bp.route("/api/download/app/<target>", methods=["GET", "HEAD"])
def download_native_app(target):
    """Phuc vu file tai ung dung da nen tang Meikova Harvest:
    Windows (.exe Setup / Portable / .msi), macOS (.dmg / .zip), Linux (.AppImage / .deb / .tar.gz), Extension."""
    target_lower = target.lower().strip()
    if target_lower not in VALID_APP_TARGETS:
        return jsonify({
            "status": "error",
            "code": "APP_TARGET_NOT_SUPPORTED",
            "message": f"Khong ho tro goi tai: {target}"
        }), 404

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if target_lower in ["extension", "chrome", "edge", "brave"]:
        ext_dir = os.path.join(root_dir, "extension")
        if os.path.isdir(ext_dir):
            import io, zipfile
            mem_buf = io.BytesIO()
            with zipfile.ZipFile(mem_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(ext_dir):
                    for file in files:
                        if file.startswith(".") or file.endswith((".tmp", ".bak", ".log", ".env")):
                            continue
                        full_p = os.path.join(root, file)
                        rel_p = os.path.relpath(full_p, ext_dir)
                        zf.write(full_p, rel_p)
            mem_buf.seek(0)
            return send_file(mem_buf, as_attachment=True, download_name="MeikovaHarvest-Extension.zip", mimetype="application/zip")
            
    # Kiem tra neu file local ton tai san trong thu muc dist_electron hoac dist
    for folder in ["dist_electron", "dist"]:
        folder_path = os.path.join(root_dir, folder)
        if os.path.isdir(folder_path):
            for f in os.listdir(folder_path):
                f_lower = f.lower()
                matched = False
                if target_lower in ("windows", "win", "win-setup", "exe") and "setup" in f_lower and f_lower.endswith(".exe"):
                    matched = True
                elif target_lower in ("win-portable", "portable") and "portable" in f_lower and f_lower.endswith(".exe"):
                    matched = True
                elif target_lower in ("msi",) and f_lower.endswith(".msi"):
                    matched = True
                elif target_lower in ("macos", "mac", "dmg") and f_lower.endswith(".dmg"):
                    matched = True
                elif target_lower in ("linux", "appimage") and f_lower.endswith(".appimage"):
                    matched = True
                elif target_lower in ("deb", "linux-deb") and f_lower.endswith(".deb"):
                    matched = True
                elif target_lower in ("tar", "linux-tar") and f_lower.endswith(".tar.gz"):
                    matched = True
                
                if matched:
                    local_f = os.path.join(folder_path, f)
                    if os.path.isfile(local_f) and os.path.getsize(local_f) > 0:
                        return send_file(local_f, as_attachment=True, download_name=f)

    # Phan giai link tai thuc te tu GitHub Releases cua Meikova
    resolved_url = resolve_target_download_url(target_lower)
    if not resolved_url:
        return jsonify({
            "status": "error",
            "code": "APP_RELEASE_ASSET_NOT_FOUND",
            "message": f"Khong tim thay ban phat hanh phu hop cho: {target}"
        }), 404

    return redirect(resolved_url, code=307)
