import socket
from flask import Blueprint, render_template, Response, jsonify, request

pages_bp = Blueprint("pages", __name__)


def _get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    return "127.0.0.1"


@pages_bp.route("/")
def index():
    return render_template("index.html")


@pages_bp.route("/api/network/host-info")
def host_info():
    lan_ip = _get_lan_ip()
    port = ""
    host_header = request.headers.get("X-Forwarded-Host", request.host)
    if ":" in host_header:
        port = host_header.split(":")[-1]
    else:
        env_port = request.environ.get("SERVER_PORT", "")
        if env_port and env_port not in ("80", "443"):
            port = env_port
        else:
            port = "5000"

    scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    lan_origin = f"{scheme}://{lan_ip}:{port}" if port and port not in ("80", "443") else f"{scheme}://{lan_ip}"
    public_origin = request.host_url.rstrip("/")

    return jsonify({
        "lan_ip": lan_ip,
        "lan_origin": lan_origin,
        "public_origin": public_origin,
        "current_origin": public_origin,
        "is_local": request.host.startswith("localhost") or request.host.startswith("127.0.0.1")
    })


@pages_bp.route("/robots.txt")
def robots_txt():
    content = "User-agent: *\nAllow: /\nDisallow: /api/\n"
    return Response(content, mimetype="text/plain")
