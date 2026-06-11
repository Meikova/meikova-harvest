import os
import threading

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Downloads directory
TEMP_DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(TEMP_DOWNLOAD_DIR, exist_ok=True)

# Global dictionary for tracking download tasks and lock for thread safety
downloads_status = {}
downloads_status_lock = threading.Lock()
