import os
import shutil
import logging
import sys
import subprocess

# Suppress console window popups for subprocesses on Windows
if sys.platform.startswith("win"):
    _original_popen = subprocess.Popen
    class PopenNoWindow(_original_popen):
        def __init__(self, *args, **kwargs):
            if 'creationflags' not in kwargs:
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)
    subprocess.Popen = PopenNoWindow

# Ensure local virtual environment site-packages take precedence over global python
_base_dir = os.path.dirname(os.path.abspath(__file__))
_venv_dir = os.path.join(_base_dir, "venv")
if os.path.isdir(_venv_dir):
    _site_pkgs = os.path.join(_venv_dir, "Lib", "site-packages") if sys.platform.startswith("win") else os.path.join(_venv_dir, f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
    if os.path.isdir(_site_pkgs) and _site_pkgs not in sys.path:
        sys.path.insert(0, _site_pkgs)

from flask import Flask, jsonify
from flask_cors import CORS
import static_ffmpeg

from config import TEMP_DOWNLOAD_DIR
from routes import pages_bp, cookies_bp, info_bp, download_bp, build_bp, extension_bp, convert_bp, auth_bp

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Install DNS bypass to handle ISP-blocked domains (common with Vietnamese ISPs)
from utils.dns_bypass import install_dns_bypass
install_dns_bypass()

# Initialize FFmpeg asynchronously in a background daemon thread so server starts instantly (<200ms)
def _init_ffmpeg_async():
    try:
        import shutil
        from config import USER_DATA_DIR

        # 1. Prepend persistent user data bin directory & known local paths to PATH
        user_bin = os.path.join(USER_DATA_DIR, "bin")
        os.makedirs(user_bin, exist_ok=True)

        base_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
        candidate_dirs = [
            user_bin,
            base_dir,
            os.path.join(base_dir, "resources"),
            os.path.join(base_dir, "bin"),
            r"C:\enviroment_dev\PYTHON\ffmpeg\bin",
        ]
        for c in candidate_dirs:
            if os.path.isdir(c) and c not in os.environ.get("PATH", ""):
                os.environ["PATH"] = c + os.pathsep + os.environ.get("PATH", "")

        # 2. Check if ffmpeg/ffprobe is already available on PATH (system or cached)
        if shutil.which("ffmpeg") and shutil.which("ffprobe"):
            logger.info("FFmpeg/FFprobe binaries already available on PATH.")
            # Cache to user_bin if not yet cached
            for bname in ["ffmpeg.exe", "ffprobe.exe", "ffmpeg", "ffprobe"]:
                src = shutil.which(bname)
                if src and os.path.isfile(src):
                    dest = os.path.join(user_bin, os.path.basename(src))
                    if not os.path.exists(dest):
                        try:
                            shutil.copy2(src, dest)
                        except Exception:
                            pass
            return

        # 3. Otherwise, fetch via static-ffmpeg in background thread
        logger.info("Resolving portable FFmpeg via static-ffmpeg in background...")
        import static_ffmpeg
        static_ffmpeg.add_paths(weak=True)
        logger.info("static-ffmpeg initialized successfully.")

        # 4. Cache downloaded binaries into persistent USER_DATA_DIR/bin
        ffmpeg_bin = shutil.which("ffmpeg")
        ffprobe_bin = shutil.which("ffprobe")
        for exe_src in [ffmpeg_bin, ffprobe_bin]:
            if exe_src and os.path.isfile(exe_src):
                dest_file = os.path.join(user_bin, os.path.basename(exe_src))
                if not os.path.exists(dest_file):
                    try:
                        shutil.copy2(exe_src, dest_file)
                        logger.info(f"Cached {os.path.basename(exe_src)} to persistent bin: {dest_file}")
                    except Exception:
                        pass
    except Exception as e:
        logger.warning(f"Background FFmpeg resolution notice: {e}")

import threading
threading.Thread(target=_init_ffmpeg_async, daemon=True, name="ffmpeg-init").start()

# Initialize Flask app with dynamic static and template resolution
def _resolve_app_asset_dir(subpath):
    candidates = [
        os.path.join(r"D:\JOB\DEV\meikova\meikova-harvest", subpath),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), subpath),
        os.path.join(os.getcwd(), subpath),
    ]
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        candidates.insert(1, os.path.join(exe_dir, subpath))
        candidates.insert(2, os.path.join(exe_dir, '..', subpath))
        meipass = getattr(sys, '_MEIPASS', '')
        if meipass:
            candidates.append(os.path.join(meipass, subpath))
    for c in candidates:
        if c and os.path.isdir(c):
            return os.path.abspath(c)
    return subpath

STATIC_DIR = _resolve_app_asset_dir("static")
TEMPLATES_DIR = _resolve_app_asset_dir("templates")
app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATES_DIR)
# Lockdown CORS to local origins and Electron webviews
CORS(
    app,
    resources={r"/api/*": {"origins": [
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        r"^file://.*",
        r"^vscode-webview://.*",
        r"^app://.*"
    ]}},
    supports_credentials=True
)

# Clean up any leftover temporary folders from previous runs on startup
logger.info("Cleaning up leftover temporary downloads...")
try:
    if os.path.exists(TEMP_DOWNLOAD_DIR):
        for item in os.listdir(TEMP_DOWNLOAD_DIR):
            if item in ["cookies", "downloads.db", "downloads.db-wal", "downloads.db-shm"]:
                continue
            item_path = os.path.join(TEMP_DOWNLOAD_DIR, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        logger.info("Leftover temporary downloads cleaned (cookies preserved).")
except Exception as e:
    logger.warning(f"Failed to clean downloads directory on startup: {e}")

# Register Blueprints
app.register_blueprint(pages_bp)
app.register_blueprint(cookies_bp)
app.register_blueprint(info_bp)
app.register_blueprint(download_bp)
app.register_blueprint(build_bp)
app.register_blueprint(extension_bp)
app.register_blueprint(convert_bp)
app.register_blueprint(auth_bp)

# Catch-all 404 handler: proxy unmatched requests from AVS player iframe to CDN
@app.errorhandler(404)
def handle_avs_proxy_fallback(e):
    from flask import request as flask_request, make_response
    referer = flask_request.headers.get("Referer", "")
    # Only proxy if the request comes from our proxy-sub iframe (player page)
    if "proxy-sub" in referer and "googleapiscdn.com" in referer:
        path = flask_request.path
        
        # Intercept and neutralize anti-devtools/anti-tamper shield script only
        if "avs-shield" in path:
            logger.info(f"Neutralizing anti-devtools shield script: {path}")
            r = make_response("console.log('AVS Shield neutralized.');", 200)
            r.headers["Content-Type"] = "application/javascript; charset=utf-8"
            r.headers["Access-Control-Allow-Origin"] = "*"
            return r
            
        import requests as req_lib
        from urllib.parse import parse_qs, urlparse
        parsed_ref = urlparse(referer)
        ref_qs = parse_qs(parsed_ref.query)
        target_domain = "storage.googleapiscdn.com"
        if "url" in ref_qs and ref_qs["url"]:
            target_domain = urlparse(ref_qs["url"][0]).netloc or "storage.googleapiscdn.com"
            
        qs = flask_request.query_string.decode("utf-8")
        target_url = f"https://{target_domain}{path}"
        if qs:
            target_url += f"?{qs}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Referer": f"https://{target_domain}/"
        }
        try:
            resp = req_lib.request(
                flask_request.method, target_url,
                headers=headers, verify=False, timeout=10,
                data=flask_request.get_data() if flask_request.method == "POST" else None
            )
            content = resp.content
            # Patch init.min.js to suppress browser upgrade notice and force player initialization
            if "init.min.js" in path:
                try:
                    js_text = content.decode("utf-8")
                    js_text = js_text.replace("function _avsShowBrowserUpgradeNotice(){", "function _avsShowBrowserUpgradeNotice(){return;")
                    js_text = js_text.replace("function _runCompatBootstrap(){", "function _runCompatBootstrap(){try{if(typeof startPlayer==='function')startPlayer();}catch(e){};return;")
                    content = js_text.encode("utf-8")
                except Exception as patch_err:
                    logger.warning(f"Failed to patch init.min.js: {patch_err}")

            r = make_response(content, resp.status_code)
            if "Content-Type" in resp.headers:
                r.headers["Content-Type"] = resp.headers["Content-Type"]
            r.headers["Access-Control-Allow-Origin"] = "*"
            return r
        except Exception:
            pass
    # Default Flask 404
    return e

@app.route("/devtools-warning")
def devtools_warning_stub():
    from flask import make_response
    logger.info("Devtools warning redirect intercepted. Returning stub page.")
    r = make_response("<html><body><script>console.warn('Devtools warning bypassed.');</script></body></html>", 200)
    r.headers["Content-Type"] = "text/html; charset=utf-8"
    return r

@app.route("/api/clear-temp", methods=["POST"])
def clear_temporary_files():
    try:
        cleaned_count = 0
        if os.path.exists(TEMP_DOWNLOAD_DIR):
            for item in os.listdir(TEMP_DOWNLOAD_DIR):
                if item in ["cookies", "downloads.db", "downloads.db-wal", "downloads.db-shm"]:
                    continue
                item_path = os.path.join(TEMP_DOWNLOAD_DIR, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                    cleaned_count += 1
                except Exception as ex:
                    logger.warning(f"Could not delete {item_path}: {ex}")
        return jsonify({"success": True, "message": "Successfully cleared temporary cache folder.", "count": cleaned_count})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/system/shutdown", methods=["POST"])
def system_shutdown():
    from flask import request
    remote = request.remote_addr or ""
    if remote not in ["127.0.0.1", "::1", "localhost"]:
        return jsonify({"success": False, "error": "Forbidden"}), 403
    logger.info("Received graceful shutdown request from Electron.")
    
    def _do_shutdown():
        import time
        time.sleep(0.3)
        try:
            import sqlite3
            from config import DB_PATH
            if os.path.exists(DB_PATH):
                conn = sqlite3.connect(DB_PATH, timeout=5.0)
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                conn.close()
        except Exception as e:
            logger.warning(f"Error during SQLite WAL checkpoint: {e}")
        os._exit(0)

    import threading
    threading.Thread(target=_do_shutdown, daemon=True).start()
    return jsonify({"success": True, "message": "Server shutting down cleanly."})

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Start Flask Server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("FLASK_PORT", 18650)))
    args = parser.parse_known_args()[0]

    # Disable reloader so file changes in downloads/ or db do not restart the server mid-download
    is_prod = os.environ.get("FLASK_ENV") == "production" or getattr(sys, "frozen", False)
    logger.info(f"Starting server on port {args.port} (debug={not is_prod})")
    app.run(host="0.0.0.0", port=args.port, debug=not is_prod, use_reloader=False, threaded=True)
