import os
import shutil
import logging
from flask import Flask
from flask_cors import CORS
import static_ffmpeg

from config import TEMP_DOWNLOAD_DIR
from routes import pages_bp, cookies_bp, info_bp, download_bp

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
            if item == "cookies":
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
