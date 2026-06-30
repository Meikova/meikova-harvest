import logging
import threading
import queue
import json
from flask import Blueprint, request, jsonify, Response

logger = logging.getLogger(__name__)

extension_bp = Blueprint("extension", __name__)

class ExtensionEventHub:
    def __init__(self):
        self.listeners = []
        self.lock = threading.Lock()

    def subscribe(self):
        q = queue.Queue(maxsize=20)
        with self.lock:
            self.listeners.append(q)
        logger.info(f"Extension SSE client subscribed. Total listeners: {len(self.listeners)}")
        return q

    def unsubscribe(self, q):
        with self.lock:
            if q in self.listeners:
                self.listeners.remove(q)
        logger.info(f"Extension SSE client unsubscribed. Total listeners: {len(self.listeners)}")

    def broadcast(self, url):
        with self.lock:
            logger.info(f"Broadcasting URL to {len(self.listeners)} listener(s): {url}")
            for q in self.listeners:
                try:
                    q.put_nowait(url)
                except queue.Full:
                    # Clear oldest item to make space
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        pass
                    try:
                        q.put_nowait(url)
                    except queue.Full:
                        pass

extension_hub = ExtensionEventHub()

@extension_bp.route("/api/extension/trigger", methods=["POST"])
def trigger_extension_url():
    data = request.get_json() or {}
    url = data.get("url")
    if not url:
        return jsonify({"status": "error", "message": "No URL provided"}), 400
    
    extension_hub.broadcast(url)
    return jsonify({"status": "success", "message": "URL successfully broadcasted to active app clients."})

@extension_bp.route("/api/extension/stream", methods=["GET"])
def stream_extension_urls():
    def event_generator():
        q = extension_hub.subscribe()
        try:
            while True:
                try:
                    # Non-blocking get with timeout to allow thread shutdown and detect closed connection
                    url = q.get(timeout=1.5)
                    yield f"data: {json.dumps({'url': url})}\n\n"
                except queue.Empty:
                    # Yield heartbeat comment to keep the SSE connection alive
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            logger.info("Extension SSE event stream generator exited.")
        finally:
            extension_hub.unsubscribe(q)

    response = Response(event_generator(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response
