import socket
from flask import Blueprint, render_template, Response, jsonify, request, redirect

pages_bp = Blueprint("pages", __name__)


def _get_network_ips():
    lan_ip = "127.0.0.1"
    tailscale_ip = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    try:
        _, _, ips = socket.gethostbyname_ex(socket.gethostname())
        for ip in ips:
            if ip.startswith("100."):
                tailscale_ip = ip
                break
        if lan_ip == "127.0.0.1":
            for ip in ips:
                if not ip.startswith("127.") and not ip.startswith("100."):
                    lan_ip = ip
                    break
    except Exception:
        pass

    return lan_ip, tailscale_ip


@pages_bp.route("/")
def index():
    return render_template("index.html")


@pages_bp.route("/api/host-info")
@pages_bp.route("/api/network/host-info")
def host_info():
    lan_ip, tailscale_ip = _get_network_ips()
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
    lan_url = f"{scheme}://{lan_ip}:{port}" if port and port not in ("80", "443") else f"{scheme}://{lan_ip}"
    tailscale_url = f"{scheme}://{tailscale_ip}:{port}" if tailscale_ip else None
    active_url = request.host_url.rstrip("/")

    return jsonify({
        "lan_ip": lan_ip,
        "lan_url": lan_url,
        "lan_origin": lan_url,  # backward compatibility alias
        "tailscale_ip": tailscale_ip,
        "tailscale_url": tailscale_url,
        "host": host_header,
        "active_url": active_url,
        "public_origin": active_url,  # backward compatibility alias
        "is_local": request.host.startswith("localhost") or request.host.startswith("127.0.0.1")
    })


@pages_bp.route("/api/qr")
def get_qr():
    data = (request.args.get("data") or "").strip()
    if not data:
        data = request.host_url.rstrip("/")
    if len(data) > 2048:
        return Response("data too long", status=400)

    try:
        import io
        import qrcode
        import qrcode.image.svg
        factory = qrcode.image.svg.SvgPathImage
        img = qrcode.make(data, image_factory=factory)
        buf = io.BytesIO()
        img.save(buf)
        return Response(
            buf.getvalue(),
            mimetype="image/svg+xml",
            headers={"Cache-Control": "public, max-age=60"}
        )
    except ImportError:
        from urllib.parse import quote
        return redirect(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={quote(data)}", code=307)


@pages_bp.route("/robots.txt")
def robots_txt():
    content = "User-agent: *\nAllow: /\nDisallow: /api/\n"
    return Response(content, mimetype="text/plain")
