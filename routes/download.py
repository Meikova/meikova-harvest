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
    thumbnail = (data.get("thumbnail") or "").strip()
    client_id = data.get("client_id")
    episode = (data.get("episode") or "").strip()
    server = (data.get("server") or "").strip()

    trim_start = data.get("trim_start")
    trim_end = data.get("trim_end")
    translate_subs = data.get("translate_subs")
    
    export_type = data.get("export_type") or "default"
    if export_type == "gif":
        ext = "gif"
        
    color_filter = data.get("color_filter") or "none"
    voiceover_active = bool(data.get("voiceover_active"))
    voiceover_voice = data.get("voiceover_voice") or "vi-VN-HoaiMyNeural"
    voiceover_rate = data.get("voiceover_rate")
    voiceover_pitch = data.get("voiceover_pitch")
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
            "url": url,
            "format_id": format_id,
            "quality": quality,
            "title": title,
            "thumbnail": thumbnail,
            "voiceover_active": voiceover_active,
            "voiceover_voice": voiceover_voice,
            "voiceover_rate": voiceover_rate,
            "voiceover_pitch": voiceover_pitch,
            "trim_start": trim_start,
            "trim_end": trim_end,
            "cloud_destination": cloud_destination,
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
            "voiceover_active": voiceover_active,
            "voiceover_voice": voiceover_voice,
            "voiceover_rate": voiceover_rate,
            "voiceover_pitch": voiceover_pitch,
            "cloud_destination": cloud_destination,
            "tg_bot_token": tg_bot_token,
            "tg_chat_id": tg_chat_id,
            "episode": episode,
            "server": server,
        }
    )
    thread.start()

    return jsonify({"status": "success", "download_id": download_id})


@download_bp.route("/api/download/history", methods=["GET"])
def get_download_history_api():
    history = downloads_status.get_history(limit=50)
    return jsonify({"status": "success", "history": history})


@download_bp.route("/api/download/history/clear", methods=["POST"])
def clear_download_history_api():
    success = downloads_status.clear_history()
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


@download_bp.route("/api/download/cancel/<download_id>", methods=["POST"])
def cancel_download(download_id):
    with downloads_status_lock:
        status_info = downloads_status.get(download_id)
        if not status_info:
            return jsonify({"status": "error", "message": "Download task not found."}), 404
        
        # Mark as cancelled
        status_info["status"] = "cancelled"
        status_info["message"] = "Download cancelled by user."
        
    logger.info(f"Task {download_id} marked as cancelled by client.")
    return jsonify({"status": "success", "message": "Cancellation request submitted."})


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
    elif ext in ["html", "htm"]:
        content_type = "text/html; charset=utf-8"
    elif ext == "txt":
        content_type = "text/plain; charset=utf-8"
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


@download_bp.route("/api/proxy/stream")
def proxy_stream():
    url = request.args.get("url")
    if not url:
        return "Missing url parameter", 400
        
    client_id = request.args.get("client_id")
    referer = get_referer_by_url(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    if referer:
        headers["Referer"] = referer
        
    # Forward Range headers to support partial content requests
    range_header = request.headers.get("Range")
    if range_header:
        headers["Range"] = range_header
        
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
                logger.warning(f"Failed to parse cookies for proxy stream: {cookie_err}")
                
    try:
        from curl_cffi import requests as curl_requests
        resp = curl_requests.get(url, headers=headers, cookies=cookies_dict, stream=True, verify=False, impersonate="chrome", timeout=12)
        
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
            import re
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
            "Content-Type": resp.headers.get("Content-Type", "video/mp4"),
            "Access-Control-Allow-Origin": "*"
        }
        
        # Forward range-request specific headers
        for h in ["Content-Range", "Accept-Ranges", "Content-Length"]:
            if h in resp.headers:
                resp_headers[h] = resp.headers[h]
                
        return Response(generate(), status=resp.status_code, headers=resp_headers)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Proxy error: {e}", 500


@download_bp.route("/api/download/history/delete/<download_id>", methods=["POST"])
def delete_download_history_item(download_id):
    data = request.get_json() or {}
    delete_file = bool(data.get("delete_file", False))
    
    with downloads_status_lock:
        status_info = downloads_status.get(download_id)
        
    if not status_info:
        return jsonify({"status": "error", "message": "Download task not found."}), 404
        
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
    audio_url = request.args.get("audio_url")
    if not video_url or not audio_url:
        return "Missing video_url or audio_url parameters", 400

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

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    headers_arg = f"User-Agent: {user_agent}\r\n"

    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except Exception as path_e:
        logger.warning(f"Failed to add static-ffmpeg paths: {path_e}")

    # Build FFmpeg command to mux video-only and audio-only URLs on-the-fly
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", start_time_str,
        "-headers", headers_arg,
        "-i", video_url,
        "-ss", start_time_str,
        "-headers", headers_arg,
        "-i", audio_url,
        "-c:v", "copy",
        "-c:a", "copy",
        "-f", fmt_flag
    ]
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
