import os
import re
import logging
from flask import Blueprint, request, jsonify
from config import TEMP_DOWNLOAD_DIR, COOKIES_DIR
from utils.cookies import parse_cookies_to_dict, serialize_netscape_cookies

cookies_bp = Blueprint("cookies", __name__)
logger = logging.getLogger(__name__)

CLIENT_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

def _validate_client_id(client_id: str) -> tuple[bool, str]:
    if not client_id or not isinstance(client_id, str):
        return False, "Client ID is required."
    clean_id = client_id.strip()
    if not clean_id:
        return False, "Client ID is required."
    if not CLIENT_ID_REGEX.match(clean_id):
        return False, "Invalid Client ID format. Allowed characters: alphanumeric, hyphen, underscore (max 64 chars)."
    return True, clean_id

def _get_safe_cookie_file(client_id: str, base_dir: str = COOKIES_DIR) -> tuple[bool, str]:
    valid, result = _validate_client_id(client_id)
    if not valid:
        return False, result
    safe_id = result
    os.makedirs(base_dir, exist_ok=True)
    real_base = os.path.realpath(base_dir)
    filepath = os.path.realpath(os.path.join(real_base, f"cookies_{safe_id}.txt"))
    try:
        if os.path.commonpath([real_base, filepath]) != real_base:
            return False, "Path traversal attempt detected."
    except ValueError:
        return False, "Path traversal attempt detected."
    return True, filepath


@cookies_bp.route("/api/cookies/upload", methods=["POST"])
def upload_cookies():
    client_id = request.form.get("client_id")
    safe, filepath_or_err = _get_safe_cookie_file(client_id)
    if not safe:
        return jsonify({"status": "error", "message": filepath_or_err}), 400
    filepath = filepath_or_err

    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "No selected file."}), 400

    try:
        content = file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to read file content: {e}"}), 400

    new_cookies = parse_cookies_to_dict(content)
    if not new_cookies:
        return jsonify({"status": "error", "message": "The uploaded cookie file is invalid or does not contain valid cookies."}), 400

    # Read existing cookies if file exists, then merge
    merged_cookies = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                existing_content = f.read()
            merged_cookies = parse_cookies_to_dict(existing_content)
        except Exception as e:
            logger.warning(f"Could not read existing cookies file for merging: {e}")

    # Merge new cookies (new overrides existing on conflict)
    merged_cookies.update(new_cookies)
    merged_content = serialize_netscape_cookies(merged_cookies)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(merged_content)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to save cookies to server: {e}"}), 500

    logger.info(f"Saved merged cookies for client {client_id}")
    return jsonify({"status": "success", "message": "Cookies uploaded and merged successfully!"})


@cookies_bp.route("/api/cookies/status", defaults={"client_id": ""}, methods=["GET"])
@cookies_bp.route("/api/cookies/status/", defaults={"client_id": ""}, methods=["GET"])
@cookies_bp.route("/api/cookies/status/<path:client_id>", methods=["GET"])
def get_cookie_status(client_id=""):
    if not client_id:
        client_id = request.args.get("client_id", "")

    safe, filepath_or_err = _get_safe_cookie_file(client_id)
    if not safe:
        return jsonify({"has_cookies": False})

    client_cookies = filepath_or_err
    if not os.path.exists(client_cookies):
        safe_temp, temp_path = _get_safe_cookie_file(client_id, os.path.join(TEMP_DOWNLOAD_DIR, "cookies"))
        if safe_temp and os.path.exists(temp_path):
            client_cookies = temp_path

    if not os.path.exists(client_cookies):
        return jsonify({"has_cookies": False})

    domains = set()
    try:
        with open(client_cookies, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        parsed = parse_cookies_to_dict(content)
        for key in parsed.keys():
            domain = key[0]
            if "facebook.com" in domain or "fb.com" in domain:
                domains.add("Facebook")
            elif "instagram.com" in domain:
                domains.add("Instagram")
            elif "youtube.com" in domain or "youtu.be" in domain:
                domains.add("YouTube")
            elif "tiktok.com" in domain:
                domains.add("TikTok")
            elif "threads.net" in domain or "threads.com" in domain:
                domains.add("Threads")
            elif "twitter.com" in domain or "x.com" in domain:
                domains.add("Twitter/X")
            elif "reddit.com" in domain:
                domains.add("Reddit")
            elif "soundcloud.com" in domain:
                domains.add("SoundCloud")
            elif "pinterest.com" in domain:
                domains.add("Pinterest")
            elif "vimeo.com" in domain:
                domains.add("Vimeo")
    except Exception as e:
        logger.warning(f"Error parsing cookies for status check: {e}")

    return jsonify({
        "has_cookies": True,
        "domains": sorted(list(domains))
    })


@cookies_bp.route("/api/cookies/paste", methods=["POST"])
def paste_cookies():
    data = request.get_json(silent=True) or {}
    client_id = data.get("client_id")
    content = data.get("content", "").strip()

    safe, filepath_or_err = _get_safe_cookie_file(client_id)
    if not safe:
        return jsonify({"status": "error", "message": filepath_or_err}), 400
    filepath = filepath_or_err

    if not content:
        return jsonify({"status": "error", "message": "Cookie content is empty."}), 400

    try:
        new_cookies = parse_cookies_to_dict(content)
        if not new_cookies:
            return jsonify({"status": "error", "message": "Cookie content is invalid or does not contain valid cookies."}), 400

        # Read existing cookies if file exists, then merge
        merged_cookies = {}
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    existing_content = f.read()
                merged_cookies = parse_cookies_to_dict(existing_content)
            except Exception as e:
                logger.warning(f"Could not read existing cookies file for merging: {e}")

        # Merge new cookies (new overrides existing on conflict)
        merged_cookies.update(new_cookies)
        merged_content = serialize_netscape_cookies(merged_cookies)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(merged_content)

        logger.info(f"Saved pasted merged cookies for client {client_id}")
        return jsonify({"status": "success", "message": "Cookies saved successfully!"})
    except Exception as e:
        logger.error(f"Failed to save pasted cookies: {e}")
        return jsonify({"status": "error", "message": f"Error saving cookies: {e}"}), 500


@cookies_bp.route("/api/cookies/clear", defaults={"client_id": ""}, methods=["POST"])
@cookies_bp.route("/api/cookies/clear/", defaults={"client_id": ""}, methods=["POST"])
@cookies_bp.route("/api/cookies/clear/<path:client_id>", methods=["POST"])
def clear_cookies(client_id=""):
    if not client_id:
        data = request.get_json(silent=True) or {}
        client_id = data.get("client_id") or request.form.get("client_id") or ""

    safe, filepath_or_err = _get_safe_cookie_file(client_id)
    if not safe:
        return jsonify({"status": "error", "message": filepath_or_err}), 400

    client_cookies = filepath_or_err
    if not os.path.exists(client_cookies):
        safe_temp, temp_path = _get_safe_cookie_file(client_id, os.path.join(TEMP_DOWNLOAD_DIR, "cookies"))
        if safe_temp and os.path.exists(temp_path):
            client_cookies = temp_path

    if os.path.exists(client_cookies):
        try:
            os.remove(client_cookies)
            logger.info(f"Cleared cookies for client {client_id}")
            return jsonify({"status": "success", "message": "Cookies cleared successfully."})
        except Exception as e:
            return jsonify({"status": "error", "message": f"Failed to clear cookies: {e}"}), 500

    return jsonify({"status": "success", "message": "No cookies found to clear."})
