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

from flask import Flask, jsonify
from flask_cors import CORS
import static_ffmpeg

from config import TEMP_DOWNLOAD_DIR
from routes import pages_bp, cookies_bp, info_bp, download_bp, build_bp

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

# Initialize Flask app
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

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

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Start Flask Server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("FLASK_PORT", 18650)))
    args = parser.parse_known_args()[0]

    # Disable debug mode in production or frozen binaries to avoid Werkzeug reloader spawn loops
    is_prod = os.environ.get("FLASK_ENV") == "production" or getattr(sys, "frozen", False)
    logger.info(f"Starting server on port {args.port} (debug={not is_prod})")
    app.run(host="0.0.0.0", port=args.port, debug=not is_prod)
