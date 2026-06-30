import os
import uuid
import logging
import time
from flask import Blueprint, request, jsonify
from config import TEMP_DOWNLOAD_DIR, downloads_status, downloads_status_lock
from tasks.convert import start_conversion_task

convert_bp = Blueprint("convert", __name__)
logger = logging.getLogger(__name__)

# Ensure upload temp directory exists
UPLOAD_DIR = os.path.join(TEMP_DOWNLOAD_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@convert_bp.route("/api/convert/upload", methods=["POST"])
def upload_local_file():
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
        
        logger.info(f"Uploaded local file to convert: {file_path}")
        return jsonify({
            "status": "success",
            "file_path": file_path,
            "filename": filename_orig,
            "size": os.path.getsize(file_path)
        })
    except Exception as e:
        logger.error(f"Failed to upload local file: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@convert_bp.route("/api/convert", methods=["POST"])
def trigger_conversion():
    data = request.get_json() or {}
    file_path = data.get("file_path")
    filename = data.get("filename")
    target_format = data.get("target_format")
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({"status": "error", "message": "Source file not found."}), 404
        
    if not target_format:
        return jsonify({"status": "error", "message": "Target format is required."}), 400
        
    task_id = f"convert-{str(uuid.uuid4())[:8]}"
    
    options = {
        "audio_bitrate": data.get("audio_bitrate", "320k"),
        "video_res": data.get("video_res", "original")
    }
    
    with downloads_status_lock:
        downloads_status[task_id] = {
            "status": "pending",
            "progress": 0,
            "message": "Initializing conversion task...",
            "title": f"Convert: {filename}",
            "filename": f"{filename.rsplit('.', 1)[0]}.{target_format}",
            "filepath": "",
            "timestamp": time.time()
        }
        
    start_conversion_task(task_id, file_path, filename, target_format, options)
    
    return jsonify({
        "status": "success",
        "download_id": task_id
    })
