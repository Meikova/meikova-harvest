import os
import logging
from flask import Blueprint, request, jsonify
from config import TEMP_DOWNLOAD_DIR, COOKIES_DIR
from utils.cookies import parse_cookies_to_dict, serialize_netscape_cookies

cookies_bp = Blueprint("cookies", __name__)
logger = logging.getLogger(__name__)


@cookies_bp.route("/api/cookies/upload", methods=["POST"])
def upload_cookies():
    client_id = request.form.get("client_id")
    if not client_id:
        return jsonify({"status": "error", "message": "Client ID is required."}), 400
        
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

    cookies_dir = COOKIES_DIR
    os.makedirs(cookies_dir, exist_ok=True)
    
    filepath = os.path.join(cookies_dir, f"cookies_{client_id}.txt")
    
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


@cookies_bp.route("/api/cookies/status/<client_id>", methods=["GET"])
def get_cookie_status(client_id):
    if not client_id:
        return jsonify({"has_cookies": False})
        
    client_cookies = os.path.join(COOKIES_DIR, f"cookies_{client_id}.txt")
    if not os.path.exists(client_cookies):
        client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")
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
    data = request.get_json() or {}
    client_id = data.get("client_id")
    content = data.get("content", "").strip()
    
    if not client_id:
        return jsonify({"status": "error", "message": "Client ID is required."}), 400
        
    if not content:
        return jsonify({"status": "error", "message": "Cookie content is empty."}), 400
        
    try:
        new_cookies = parse_cookies_to_dict(content)
        if not new_cookies:
            return jsonify({"status": "error", "message": "Cookie content is invalid or does not contain valid cookies."}), 400

        cookies_dir = COOKIES_DIR
        os.makedirs(cookies_dir, exist_ok=True)
        
        filepath = os.path.join(cookies_dir, f"cookies_{client_id}.txt")
        
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


@cookies_bp.route("/api/cookies/clear/<client_id>", methods=["POST"])
def clear_cookies(client_id):
    if not client_id:
        return jsonify({"status": "error", "message": "Client ID is required."}), 400
        
    client_cookies = os.path.join(COOKIES_DIR, f"cookies_{client_id}.txt")
    if not os.path.exists(client_cookies):
        client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")
    if os.path.exists(client_cookies):
        try:
            os.remove(client_cookies)
            logger.info(f"Cleared cookies for client {client_id}")
            return jsonify({"status": "success", "message": "Cookies cleared successfully."})
        except Exception as e:
            return jsonify({"status": "error", "message": f"Failed to clear cookies: {e}"}), 500
    return jsonify({"status": "success", "message": "No cookies found to clear."})
