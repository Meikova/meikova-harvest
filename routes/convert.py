import os
import uuid
import logging
import time
from flask import Blueprint, request, jsonify, send_file
from config import TEMP_DOWNLOAD_DIR, downloads_status, downloads_status_lock
from tasks.convert import start_conversion_task, probe_media_file
from routes.auth import get_authenticated_user

convert_bp = Blueprint("convert", __name__)
logger = logging.getLogger(__name__)

# Ensure upload temp directory exists
UPLOAD_DIR = os.path.join(TEMP_DOWNLOAD_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@convert_bp.route("/api/convert/upload", methods=["POST"])
def upload_local_file():
    """Fallback file uploader for web/browser environment."""
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded."}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "No file selected."}), 400
    
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        filename_orig = file.filename
        ext = filename_orig.rsplit(".", 1)[-1] if "." in filename_orig else ""
        unique_id = str(uuid.uuid4())
        safe_filename = f"{unique_id}.{ext}" if ext else unique_id
        
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        file.save(file_path)
        
        logger.info(f"Uploaded file for conversion: {file_path}")
        probe_data = probe_media_file(file_path) or {}
        
        return jsonify({
            "status": "success",
            "file_path": file_path,
            "filename": filename_orig,
            "size": os.path.getsize(file_path),
            "probe": probe_data
        })
    except Exception as e:
        logger.error(f"Failed to upload local file: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@convert_bp.route("/api/convert/probe", methods=["POST"])
def probe_file():
    """Inspects a local media file to extract codecs, duration, dimensions, and audio channels."""
    data = request.get_json() or {}
    file_path = data.get("file_path", "").strip()
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({"status": "error", "message": "File not found on system."}), 404

    from utils.security import is_safe_local_media_path
    safe, reason = is_safe_local_media_path(file_path, allow_user_local_media=True)
    if not safe:
        return jsonify({"status": "error", "message": f"Security restriction: {reason}"}), 403
        
    try:
        probe_info = probe_media_file(file_path)
        if not probe_info:
            return jsonify({"status": "error", "message": "Could not inspect media streams."}), 400
            
        return jsonify({
            "status": "success",
            "probe": probe_info
        })
    except Exception as e:
        logger.error(f"Error probing file {file_path}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@convert_bp.route("/api/convert/preview-stream")
def preview_local_stream():
    """Streams local audio/video with HTTP Range support for converter preview player."""
    file_path = request.args.get("file_path", "").strip()
    if not file_path or not os.path.exists(file_path):
        return jsonify({"status": "error", "message": "File not found on system."}), 404

    from utils.security import is_safe_local_media_path
    safe, reason = is_safe_local_media_path(file_path, allow_user_local_media=True)
    if not safe:
        return jsonify({"status": "error", "message": f"Security restriction: {reason}"}), 403
        
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    mime_map = {
        "mp4": "video/mp4", "mkv": "video/x-matroska", "webm": "video/webm",
        "mov": "video/quicktime", "avi": "video/x-msvideo", "ts": "video/mp2t",
        "mp3": "audio/mpeg", "wav": "audio/wav", "flac": "audio/flac",
        "m4a": "audio/mp4", "ogg": "audio/ogg", "opus": "audio/opus",
        "gif": "image/gif", "webp": "image/webp",
        "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
        "bmp": "image/bmp", "ico": "image/x-icon", "tiff": "image/tiff",
        "svg": "image/svg+xml", "avif": "image/avif"
    }
    mimetype = mime_map.get(ext, "application/octet-stream")
    try:
        return send_file(file_path, mimetype=mimetype, conditional=True)
    except Exception as e:
        logger.error(f"Error streaming preview for {file_path}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@convert_bp.route("/api/convert", methods=["POST"])
def trigger_conversion():
    data = request.get_json() or {}
    file_path = data.get("file_path")
    filename = data.get("filename") or os.path.basename(file_path or "media")
    target_format = (data.get("target_format") or "").strip().lower()
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({"status": "error", "message": "Source file not found on disk."}), 404

    from utils.security import is_safe_local_media_path
    safe, reason = is_safe_local_media_path(file_path, allow_user_local_media=True)
    if not safe:
        return jsonify({"status": "error", "message": f"Security restriction: {reason}"}), 403
        
    if not target_format:
        return jsonify({"status": "error", "message": "Target format is required."}), 400
        
    task_id = f"convert-{str(uuid.uuid4())[:8]}"
    
    # Comprehensive options mapping
    options = {
        "video_codec": data.get("video_codec", "auto"),
        "video_res": data.get("video_res", "original"),
        "video_fps": data.get("video_fps", "original"),
        "video_crf": data.get("video_crf", "23"),
        "audio_bitrate": data.get("audio_bitrate", "320k"),
        "audio_channels": data.get("audio_channels", "original"),
        "audio_volume": data.get("audio_volume", "100"),
        "mute_audio": data.get("mute_audio", False),
        "trim_start": data.get("trim_start"),
        "trim_end": data.get("trim_end"),
        "gif_fps": data.get("gif_fps", "15"),
        "gif_scale": data.get("gif_scale", "480"),
        "passthrough": data.get("passthrough", False)
    }
    
    clean_base = filename.rsplit(".", 1)[0] if "." in filename else filename
    target_filename = f"{clean_base}.{target_format}"
    
    current_user = get_authenticated_user()
    user_id = current_user["id"] if current_user else None

    with downloads_status_lock:
        downloads_status[task_id] = {
            "status": "pending",
            "progress": 0,
            "message": "Initializing conversion engine...",
            "title": f"Convert: {filename}",
            "filename": target_filename,
            "filepath": "",
            "timestamp": time.time(),
            "user_id": user_id
        }
        
    start_conversion_task(task_id, file_path, filename, target_format, options)
    
    return jsonify({
        "status": "success",
        "download_id": task_id,
        "filename": target_filename
    })
