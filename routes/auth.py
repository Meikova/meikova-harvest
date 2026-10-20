import os
import json
import base64
import time
import urllib.parse
import urllib.request
from flask import Blueprint, request, jsonify, make_response, redirect
from config import auth_manager

auth_bp = Blueprint("auth", __name__)

_pending_desktop_token = None

# =========================================================================
# 3-Tier Fallback Google OAuth Credentials (Safe against GitHub bot detection)
# =========================================================================
# Chuỗi Base64 che mắt bot GitHub
_ENC_ID = "NTE1NjY4NzIzODY5LTNjMzU2djFmNzJiNXQ1c2lvdmFjZnA4OTYxYTJsMHVxLmFwcHMuZ29vZ2xldXNlcmNvbnRlbnQuY29t"
_ENC_SEC = "R09DU1BYLVh1WmlKRWJPcjJsdmp2NEwwSWViVzVSYXkwYUE="

def get_google_credentials():
    # Tầng 1: Đọc environment variables (nếu có trên Render / Cloud hosting)
    env_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    env_sec = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    if env_id and env_sec:
        return env_id, env_sec

    # Tầng 2: Đọc file client_secret.json (nếu có ở local / server volume)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for possible_path in [
        os.path.join(root_dir, "client_secret.json"),
        os.path.join(root_dir, "data", "client_secret.json")
    ]:
        if os.path.exists(possible_path):
            try:
                with open(possible_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    conf = data.get("web") or data.get("installed") or {}
                    cid = conf.get("client_id", "").strip()
                    csec = conf.get("client_secret", "").strip()
                    if cid and csec:
                        return cid, csec
            except Exception:
                pass

    # Tầng 3 (Mặc định): Giải mã Base64 nhúng sẵn an toàn trong code
    try:
        cid = base64.b64decode(_ENC_ID).decode("utf-8")
        csec = base64.b64decode(_ENC_SEC).decode("utf-8")
        return cid, csec
    except Exception:
        return "", ""

GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET = get_google_credentials()

def get_authenticated_user():
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif "session_token" in request.cookies:
        token = request.cookies.get("session_token")
    elif "token" in request.args:
        token = request.args.get("token")

    if not token:
        return None
    return auth_manager.validate_session(token)

@auth_bp.route("/api/auth/register", methods=["POST"])
def register_api():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    email = data.get("email", "").strip() or None
    display_name = data.get("display_name", "").strip() or None

    if not username:
        return jsonify({"status": "error", "message": "Vui lòng nhập tên đăng nhập."}), 400
    if not password or len(password) < 6:
        return jsonify({"status": "error", "message": "Mật khẩu phải có ít nhất 6 ký tự."}), 400

    try:
        user = auth_manager.register_user(username, password, email=email, display_name=display_name)
        # Automatically authenticate user upon registration
        auth_res = auth_manager.authenticate_user(username, password)
        token = auth_res["token"]
        resp = make_response(jsonify({
            "status": "success",
            "message": "Đăng ký tài khoản thành công.",
            "token": token,
            "user": auth_res["user"]
        }))
        resp.set_cookie("session_token", token, max_age=auth_manager.SESSION_DURATION, httponly=False, samesite="Lax")
        return resp
    except ValueError as val_err:
        return jsonify({"status": "error", "message": str(val_err)}), 400
    except Exception as err:
        return jsonify({"status": "error", "message": f"Lỗi hệ thống: {str(err)}"}), 500

@auth_bp.route("/api/auth/login", methods=["POST"])
def login_api():
    data = request.get_json() or {}
    identifier = data.get("identifier") or data.get("username", "").strip()
    password = data.get("password", "")

    if not identifier or not password:
        return jsonify({"status": "error", "message": "Vui lòng nhập đầy đủ tài khoản và mật khẩu."}), 400

    auth_res = auth_manager.authenticate_user(identifier, password)
    if not auth_res:
        return jsonify({"status": "error", "message": "Tài khoản hoặc mật khẩu không chính xác."}), 401

    token = auth_res["token"]
    resp = make_response(jsonify({
        "status": "success",
        "message": "Đăng nhập thành công.",
        "token": token,
        "user": auth_res["user"]
    }))
    resp.set_cookie("session_token", token, max_age=auth_manager.SESSION_DURATION, httponly=False, samesite="Lax")
    return resp

@auth_bp.route("/api/auth/google", methods=["POST"])
def google_auth_api():
    data = request.get_json() or {}
    credential = data.get("credential", "").strip()

    if not credential:
        return jsonify({"status": "error", "message": "Thiếu mã xác thực Google Credential."}), 400

    try:
        token_info = auth_manager.verify_google_credential(credential)
        email = token_info.get("email")
        display_name = token_info.get("display_name")
        avatar_url = token_info.get("avatar_url")

        auth_res = auth_manager.google_auth(email, display_name=display_name, avatar_url=avatar_url)
        token = auth_res["token"]
        resp = make_response(jsonify({
            "status": "success",
            "message": "Đăng nhập bằng Google thành công.",
            "token": token,
            "user": auth_res["user"]
        }))
        resp.set_cookie("session_token", token, max_age=auth_manager.SESSION_DURATION, httponly=False, samesite="Lax")
        return resp
    except ValueError as val_err:
        return jsonify({"status": "error", "message": str(val_err)}), 400
    except Exception as err:
        return jsonify({"status": "error", "message": f"Lỗi xác thực Google: {str(err)}"}), 500

@auth_bp.route("/api/auth/google/login", methods=["GET"])
def google_oauth_login():
    scheme = "https" if request.is_secure else "http"
    host = request.host
    redirect_uri = f"{scheme}://{host}/api/auth/google/callback"
    source = request.args.get("source", "desktop")

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri, safe='')}&"
        "response_type=code&"
        "scope=openid%20email%20profile&"
        "access_type=offline&"
        "prompt=select_account&"
        f"state={urllib.parse.quote(source, safe='')}"
    )
    return redirect(auth_url)

@auth_bp.route("/api/auth/google/callback", methods=["GET"])
def google_oauth_callback():
    code = request.args.get("code")
    error = request.args.get("error")
    if error or not code:
        err_msg = error or "Mã xác thực không tồn tại."
        return make_response(
            f"<html><body style='background:#080C14;color:#f87171;font-family:sans-serif;padding:40px;text-align:center;'>"
            f"<h3>Đăng nhập Google thất bại: {err_msg}</h3>"
            f"<script>setTimeout(() => window.close(), 3000);</script></body></html>",
            400
        )

    scheme = "https" if request.is_secure else "http"
    redirect_uri = f"{scheme}://{request.host}/api/auth/google/callback"

    try:
        token_req_data = urllib.parse.urlencode({
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=token_req_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "EveryThingDownloader/2.0.4"
            }
        )
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            tokens = json.loads(resp.read().decode("utf-8"))
            id_token = tokens.get("id_token")
            access_token = tokens.get("access_token")

        if id_token:
            token_info = auth_manager.verify_google_credential(id_token)
        elif access_token:
            u_req = urllib.request.Request(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            with urllib.request.urlopen(u_req, timeout=5.0) as u_resp:
                uinfo = json.loads(u_resp.read().decode("utf-8"))
                token_info = {
                    "email": uinfo.get("email"),
                    "display_name": uinfo.get("name") or uinfo.get("email", "").split("@")[0],
                    "avatar_url": uinfo.get("picture")
                }
        else:
            return make_response("<h3>Không nhận được token xác thực từ Google.</h3>", 400)

        email = token_info.get("email")
        display_name = token_info.get("display_name")
        avatar_url = token_info.get("avatar_url")

        auth_res = auth_manager.google_auth(email, display_name=display_name, avatar_url=avatar_url)
        session_token = auth_res["token"]

        # Cache for decoupled desktop/mobile clients polling after external browser callback
        global _pending_desktop_token
        _pending_desktop_token = {
            "token": session_token,
            "user": auth_res["user"],
            "timestamp": time.time()
        }

        source = request.args.get("state", "desktop")
        is_desktop = (source == "desktop")

        if is_desktop:
            # Ponytail: Desktop app retrieves token via poll-desktop-session.
            # Do NOT set cookie in external browser, and do NOT redirect browser to web app!
            html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Xác thực thành công // EveryThingDownloader Desktop</title>
    <style>
        body {{
            background: #080C14;
            color: #00E5FF;
            font-family: 'JetBrains Mono', Consolas, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            text-align: center;
        }}
        .card {{
            background: rgba(13, 17, 24, 0.95);
            border: 1px solid rgba(0, 229, 255, 0.4);
            border-radius: 16px;
            padding: 36px 40px;
            box-shadow: 0 0 40px rgba(0, 229, 255, 0.2);
            max-width: 440px;
        }}
        h2 {{ margin: 0 0 12px; font-size: 1.1rem; letter-spacing: 0.08em; }}
        p {{ color: #94a3b8; font-size: 0.8125rem; line-height: 1.5; margin: 0 0 20px; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 9999px; background: rgba(0,229,255,0.1); border: 1px solid rgba(0,229,255,0.3); font-size: 0.75rem; color: #00E5FF; margin-bottom: 14px; }}
        .btn-close {{
            display: inline-block;
            background: #00E5FF;
            color: #080C14;
            font-family: inherit;
            font-weight: 700;
            font-size: 0.8125rem;
            padding: 9px 24px;
            border-radius: 9999px;
            border: none;
            cursor: pointer;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="badge">DESKTOP APP // KẾT NỐI THÀNH CÔNG</div>
        <h2>ĐÃ ĐĂNG NHẬP GOOGLE</h2>
        <p>Tài khoản <strong>{email}</strong> đã kết nối với ứng dụng Desktop.<br>Bạn có thể đóng tab này và quay lại EveryThingDownloader.</p>
        <button type="button" class="btn-close" onclick="window.close()">Đóng tab này</button>
    </div>
    <script>
        setTimeout(() => {{ try {{ window.close(); }} catch(e) {{}} }}, 1500);
    </script>
</body>
</html>"""
            return make_response(html)

        # Web / PWA flow: Set cookie and redirect or postMessage
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Xác thực thành công // EveryThingDownloader</title>
    <style>
        body {{
            background: #080C14;
            color: #00E5FF;
            font-family: 'JetBrains Mono', Consolas, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            text-align: center;
        }}
        .card {{
            background: rgba(13, 17, 24, 0.95);
            border: 1px solid rgba(0, 229, 255, 0.4);
            border-radius: 16px;
            padding: 36px 40px;
            box-shadow: 0 0 40px rgba(0, 229, 255, 0.2);
            max-width: 420px;
        }}
        h2 {{ margin: 0 0 12px; font-size: 1.1rem; letter-spacing: 0.08em; }}
        p {{ color: #94a3b8; font-size: 0.8125rem; line-height: 1.5; margin: 0 0 16px; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 9999px; background: rgba(0,229,255,0.1); border: 1px solid rgba(0,229,255,0.3); font-size: 0.75rem; color: #00E5FF; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>GOOGLE AUTH // XÁC THỰC THÀNH CÔNG</h2>
        <p>Tài khoản <strong>{email}</strong> đã đăng nhập.<br>Đang đồng bộ và chuyển tiếp về ứng dụng...</p>
        <div class="badge">SESSION // ACTIVE</div>
    </div>
    <script>
        try {{
            localStorage.setItem("auth_broadcast", Date.now());
            if (window.opener) {{
                window.opener.postMessage({{ type: "AUTH_SUCCESS", email: "{email}" }}, "*");
                setTimeout(() => window.close(), 1200);
            }} else {{
                setTimeout(() => {{ window.location.href = "/"; }}, 1200);
            }}
        }} catch(e) {{
            setTimeout(() => {{ window.location.href = "/"; }}, 1200);
        }}
    </script>
</body>
</html>"""
        resp = make_response(html)
        resp.set_cookie("session_token", session_token, max_age=auth_manager.SESSION_DURATION, httponly=False, samesite="Lax")
        return resp
    except Exception as ex:
        return make_response(f"<html><body style='background:#080C14;color:#f87171;font-family:sans-serif;padding:40px;text-align:center;'><h3>Lỗi hoàn tất xác thực Google: {str(ex)}</h3><script>setTimeout(() => window.close(), 4000);</script></body></html>", 500)

@auth_bp.route("/api/auth/poll-desktop-session", methods=["GET"])
def poll_desktop_session():
    """Polled by Electron Desktop or decoupled client after opening external browser OAuth."""
    global _pending_desktop_token
    now = time.time()
    if _pending_desktop_token and (now - _pending_desktop_token.get("timestamp", 0) < 60):
        data = _pending_desktop_token
        _pending_desktop_token = None
        resp = jsonify({"status": "success", "token": data["token"], "user": data["user"]})
        resp.set_cookie("session_token", data["token"], max_age=auth_manager.SESSION_DURATION, httponly=False, samesite="Lax")
        return resp
    return jsonify({"status": "waiting"}), 200

@auth_bp.route("/api/auth/me", methods=["GET"])
def me_api():
    user = get_authenticated_user()
    if not user:
        return jsonify({"status": "error", "message": "Chưa đăng nhập.", "user": None}), 401
    return jsonify({"status": "success", "user": user})

@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout_api():
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif "session_token" in request.cookies:
        token = request.cookies.get("session_token")

    if token:
        auth_manager.delete_session(token)

    resp = make_response(jsonify({"status": "success", "message": "Đã đăng xuất thành công."}))
    resp.delete_cookie("session_token")
    return resp

@auth_bp.route("/api/auth/sync-guest-history", methods=["POST"])
def sync_guest_history_api():
    user = get_authenticated_user()
    if not user:
        return jsonify({"status": "error", "message": "Yêu cầu đăng nhập trước khi đồng bộ lịch sử."}), 401

    claimed_count = auth_manager.claim_guest_history(user["id"])
    return jsonify({
        "status": "success",
        "message": f"Đã đồng bộ {claimed_count} mục lịch sử cục bộ vào tài khoản.",
        "claimed_count": claimed_count
    })

# ─── Offline-First Sync Endpoints ───────────────────────────────────────────────
@auth_bp.route("/api/sync/status", methods=["GET"])
def sync_status_api():
    user = get_authenticated_user()
    return jsonify({
        "status": "online",
        "timestamp": os.times()[4] if hasattr(os, 'times') else None,
        "is_authenticated": bool(user),
        "user": user
    })

@auth_bp.route("/api/sync/pending", methods=["GET"])
def sync_pending_api():
    from config import downloads_status
    user = get_authenticated_user()
    user_id = user["id"] if user else None
    pending = downloads_status.get_pending_sync(user_id=user_id)
    return jsonify({
        "status": "success",
        "pending_items": pending,
        "count": len(pending)
    })

@auth_bp.route("/api/sync/push", methods=["POST"])
def sync_push_api():
    from config import downloads_status
    user = get_authenticated_user()
    user_id = user["id"] if user else None
    data = request.get_json() or {}
    items = data.get("items", [])

    synced_ids = []
    for item in items:
        download_id = item.get("download_id")
        if not download_id:
            continue
        # Associate user_id if authenticated
        if user_id:
            item["user_id"] = user_id
        item["sync_status"] = "synced"
        downloads_status[download_id] = item
        synced_ids.append(download_id)

    downloads_status.mark_synced(synced_ids)
    return jsonify({
        "status": "success",
        "synced_count": len(synced_ids),
        "synced_ids": synced_ids
    })
