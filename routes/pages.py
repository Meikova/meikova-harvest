from flask import Blueprint, render_template, Response

pages_bp = Blueprint("pages", __name__)

@pages_bp.route("/")
def index():
    return render_template("index.html")


@pages_bp.route("/robots.txt")
def robots_txt():
    content = "User-agent: *\nAllow: /\nDisallow: /api/\n"
    return Response(content, mimetype="text/plain")
