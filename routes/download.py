import os
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
from flask import Blueprint, request, jsonify, send_file, Response

from config import TEMP_DOWNLOAD_DIR, downloads_status, downloads_status_lock
from utils.helpers import get_referer_by_url
from tasks import bg_download_task

download_bp = Blueprint("download", __name__)
logger = logging.getLogger(__name__)


@download_bp.route("/api/download", methods=["POST"])
def start_download():
    data = request.get_json() or {}
    url = (data.get("url") or "").strip()
    if "tiktok.com" in url.lower() and "/photo/" in url.lower():
        url = re.sub(r'/photo/', '/video/', url, flags=re.IGNORECASE)
    format_id = (data.get("format_id") or "").strip()
    ext = (data.get("ext") or "mp4").strip()
    quality = (data.get("quality") or "192").strip()
    title = (data.get("title") or "media").strip()
    client_id = data.get("client_id")

    trim_start = data.get("trim_start")
    trim_end = data.get("trim_end")
    translate_subs = data.get("translate_subs")
    
    export_type = data.get("export_type") or "default"
    if export_type == "gif":
        ext = "gif"
        
    color_filter = data.get("color_filter") or "none"
    voiceover_active = bool(data.get("voiceover_active"))
    voiceover_voice = data.get("voiceover_voice") or "vi-VN-HoaiMyNeural"
    cloud_destination = data.get("cloud_destination") or "local"
    tg_bot_token = data.get("tg_bot_token")
    tg_chat_id = data.get("tg_chat_id")

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
            "voiceover_active": voiceover_active,
            "voiceover_voice": voiceover_voice,
            "cloud_destination": cloud_destination,
            "tg_bot_token": tg_bot_token,
            "tg_chat_id": tg_chat_id,
        }
    )
    thread.start()

    return jsonify({"status": "success", "download_id": download_id})


@download_bp.route("/api/download/status/<download_id>", methods=["GET"])
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
        "speed": status_info.get("speed", ""),
        "eta": status_info.get("eta", ""),
    })


@download_bp.route("/api/download/progress/<download_id>", methods=["GET"])
def get_download_progress_sse(download_id):
    def event_generator():
        # Keep track of active state
        while True:
            with downloads_status_lock:
                status_info = downloads_status.get(download_id)
            
            if not status_info:
                err_data = {"status": "error", "message": "Download task not found.", "progress": 0}
                yield f"data: {json.dumps(err_data)}\n\n"
                break
            
            # Formulate update data
            data = {
                "status": status_info["status"],
                "progress": status_info["progress"],
                "message": status_info["message"],
                "ext": status_info.get("ext", ""),
                "error": status_info.get("error"),
                "speed": status_info.get("speed", ""),
                "eta": status_info.get("eta", ""),
            }
            
            yield f"data: {json.dumps(data)}\n\n"
            
            # Check for termination conditions
            if status_info["status"] in ["complete", "error"]:
                break
                
            time.sleep(0.5) # Send updates every 500ms for extra responsiveness
            
    response = Response(event_generator(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@download_bp.route("/api/download/file/<download_id>", methods=["GET"])
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
    filename = status_info["filename"]
    ext = filepath.rsplit(".", 1)[-1] if "." in filepath else "mp4"

    if not os.path.exists(filepath):
        return jsonify({"status": "error", "message": "File not found on server."}), 404

    if ext == "mp3":
        content_type = "audio/mpeg"
    elif ext == "m4a":
        content_type = "audio/mp4"
    elif ext == "vtt":
        content_type = "text/vtt"
    else:
        content_type = "video/mp4"

    preview_mode = request.args.get("preview", "false").lower() == "true"

    return send_file(
        filepath,
        mimetype=content_type,
        as_attachment=not preview_mode,
        download_name=filename,
        conditional=True
    )


@download_bp.route("/api/download/image", methods=["GET"])
def download_image():
    url = request.args.get("url")
    filename = request.args.get("filename") or "image.jpg"
    client_id = request.args.get("client_id")
    if not url:
        return "Missing url parameter", 400
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": get_referer_by_url(url)
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
                except Exception as cookie_err:
                    logger.warning(f"Failed to parse cookies file {client_cookies}: {cookie_err}")

        resp = requests.get(url, headers=headers, cookies=cookies_dict, stream=True, timeout=15)
        if resp.status_code == 200:
            fallback_filename = "image.jpg"
            encoded_filename = quote(filename)
            resp_headers = {
                "Content-Disposition": f'attachment; filename="{fallback_filename}"; filename*=UTF-8\'\'{encoded_filename}',
                "Content-Type": resp.headers.get("Content-Type", "image/jpeg")
            }
            return Response(resp.content, headers=resp_headers)
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
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": get_referer_by_url(url)
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
                except Exception as cookie_err:
                    logger.warning(f"Failed to parse cookies file {client_cookies}: {cookie_err}")

        resp = requests.get(url, headers=headers, cookies=cookies_dict, timeout=15)
        if resp.status_code == 200:
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            # Detect anti-bot block pages: CDN returns HTML instead of image
            if content_type.startswith("text/html") or (resp.content[:50].strip().startswith(b"<") and not content_type.startswith("image/")):
                logger.warning(f"Proxy image blocked by CDN (HTML response): {url[:120]}")
                return "CDN blocked the request (anti-bot)", 502
            if not content_type.startswith("image/"):
                content_type = "image/jpeg"
            return Response(resp.content, mimetype=content_type)
        else:
            return f"Failed to proxy image: HTTP {resp.status_code}", resp.status_code
    except Exception as e:
        return f"Error: {e}", 500


@download_bp.route("/api/download/images/zip", methods=["POST"])
def download_images_zip():
    data = request.get_json() or {}
    urls = data.get("urls", [])
    title = data.get("title", "images")
    client_id = data.get("client_id")
    if not urls:
        return jsonify({"status": "error", "message": "No urls provided"}), 400
    try:
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
                except Exception as cookie_err:
                    logger.warning(f"Failed to parse cookies file {client_cookies}: {cookie_err}")
        
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            for idx, item in enumerate(urls):
                url = item.get("url")
                label = item.get("label", f"image_{idx+1}")
                ext = item.get("ext", "jpg")
                if not url:
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
                    
        memory_file.seek(0)
        return send_file(
            memory_file,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{title}_images.zip"
        )
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to create ZIP: {e}"}), 500
