import os
import sys
import logging
import shutil
import yt_dlp
from config import TEMP_DOWNLOAD_DIR

try:
    from yt_dlp.networking.impersonate import ImpersonateTarget
except ImportError:
    ImpersonateTarget = None

def should_use_impersonate():
    # Disable on Windows due to curl-cffi / OpenSSL DLL conflict causing TLS connect errors
    if sys.platform.startswith("win"):
        return False
    return ImpersonateTarget is not None

logger = logging.getLogger(__name__)

# Monkey-patch CurlCFFIRH to dynamically match the TLS fingerprint with the request's User-Agent
try:
    from yt_dlp.networking._curlcffi import CurlCFFIRH
    if ImpersonateTarget and CurlCFFIRH:
        original_get_request_target = CurlCFFIRH._get_request_target

        def custom_get_request_target(self, request):
            ua = request.headers.get('User-Agent', '')
            if ua:
                ua_lower = ua.lower()
                if 'firefox' in ua_lower:
                    target_str = 'firefox'
                elif 'safari' in ua_lower and 'chrome' not in ua_lower and 'chromium' not in ua_lower:
                    target_str = 'safari'
                elif 'edge' in ua_lower or 'edg/' in ua_lower:
                    target_str = 'edge'
                elif 'android' in ua_lower:
                    target_str = 'chrome-131:android-14'
                else:
                    target_str = 'chrome'
                try:
                    resolved = self._resolve_target(ImpersonateTarget.from_str(target_str))
                    if resolved:
                        return resolved
                except Exception:
                    pass
            return original_get_request_target(self, request)

        CurlCFFIRH._get_request_target = custom_get_request_target
        logger.info("Successfully monkey-patched CurlCFFIRH._get_request_target to align TLS fingerprint with User-Agent.")
except Exception as patch_err:
    logger.warning(f"Could not monkey-patch CurlCFFIRH: {patch_err}")


_last_ytdlp_update = 0


def _find_js_runtimes():
    from pathlib import Path
    runtimes = {}
    deno_dir = Path.home() / ".local" / "bin"
    deno_bin = deno_dir / ("deno.exe" if sys.platform.startswith("win") else "deno")
    if deno_bin.exists():
        runtimes["deno"] = {"path": str(deno_bin)}
    for rt in ("deno", "node", "bun", "quickjs"):
        if rt not in runtimes:
            p = shutil.which(rt)
            runtimes[rt] = {"path": p} if p else {}
    return runtimes


def _ensure_deno():
    if sys.platform.startswith("win"):
        return
    import subprocess, re
    from pathlib import Path
    deno_dir = Path.home() / ".local" / "bin"
    deno_bin = deno_dir / "deno"

    needs_install = True
    p = shutil.which("deno") or (str(deno_bin) if deno_bin.exists() else None)
    if p:
        try:
            out = subprocess.check_output([p, "--version"], stderr=subprocess.STDOUT, text=True)
            v_match = re.search(r"deno\s+(\d+)\.(\d+)", out)
            if v_match:
                major, minor = int(v_match.group(1)), int(v_match.group(2))
                if (major, minor) >= (2, 0):
                    needs_install = False
                    if str(deno_dir) not in os.environ.get("PATH", ""):
                        os.environ["PATH"] = f"{deno_dir}:{os.environ.get('PATH', '')}"
                    logger.info(f"Deno runtime verified: {v_match.group(0)} at {p}")
        except Exception:
            pass

    if not needs_install:
        return

    try:
        import urllib.request, zipfile, io
        logger.info("Auto-installing Deno JS engine (v2.9.7 >= 2.0.0 required by yt-dlp)...")
        deno_dir.mkdir(parents=True, exist_ok=True)
        url = "https://github.com/denoland/deno/releases/download/v2.9.7/deno-x86_64-unknown-linux-gnu.zip"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            z = zipfile.ZipFile(io.BytesIO(resp.read()))
            z.extract("deno", str(deno_dir))
        deno_bin.chmod(0o755)
        os.environ["PATH"] = f"{deno_dir}:{os.environ.get('PATH', '')}"
        logger.info(f"Deno v2.9.7 installed successfully at {deno_bin}")
    except Exception as e:
        logger.warning(f"Deno auto-install skipped: {e}")


def auto_update_ytdlp(force=False):
    """Auto-updates yt-dlp and yt-dlp-ejs via pip in a background daemon thread."""
    global _last_ytdlp_update
    import time
    import threading
    import subprocess
    now = time.time()
    if not force and (now - _last_ytdlp_update < 21600):
        return
    _last_ytdlp_update = now

    def _worker():
        try:
            logger.info("Checking for yt-dlp updates via pip...")
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp", "yt-dlp-ejs"]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90)
            if res.returncode == 0:
                summary = res.stdout.strip().splitlines()[-1] if res.stdout else "Up to date"
                logger.info(f"yt-dlp auto-update check finished: {summary}")
            else:
                logger.warning(f"yt-dlp auto-update returned code {res.returncode}: {res.stderr.strip()[:200]}")
        except Exception as e:
            logger.warning(f"yt-dlp auto-update skipped: {e}")

    threading.Thread(target=_worker, daemon=True, name="ytdlp-auto-updater").start()


def resolve_youtube_oembed(video_id_or_url: str) -> dict | None:
    """Extracts public YouTube video metadata via Google's official oEmbed API.
    Bypasses datacenter bot verification / CAPTCHA completely."""
    import re
    import json
    import urllib.request
    
    video_id = video_id_or_url
    if "http" in video_id_or_url or "/" in video_id_or_url:
        m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})", video_id_or_url)
        if m:
            video_id = m.group(1)
        else:
            return None
            
    if not re.match(r"^[A-Za-z0-9_-]{11}$", video_id):
        return None

    try:
        req = urllib.request.Request(
            f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            title = data.get("title") or video_id
            author = data.get("author_name") or ""
            thumb = data.get("thumbnail_url") or f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"
            return {
                "id": video_id,
                "source": "youtube",
                "title": title,
                "channel": author,
                "duration": None,
                "thumbnail": thumb,
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }
    except Exception as e:
        logger.debug(f"oEmbed resolution failed for {video_id}: {e}")
        return None


def create_ydl_instance(ydl_opts, url=None, client_id=None):
    """
    Attempts to instantiate YoutubeDL. 
    If cookiesfrombrowser is 'auto', it will attempt different browsers one by one.
    If all fail, it will fall back to using no cookies.
    """
    logger.info(f"create_ydl_instance: client_id='{client_id}', url='{url}'")
    
    # Ensure JS runtimes are registered (Deno, Node, Bun, QuickJS)
    runtimes = _find_js_runtimes()
    if "js_runtimes" not in ydl_opts or not ydl_opts["js_runtimes"]:
        ydl_opts["js_runtimes"] = runtimes
    else:
        for rt, rt_dict in runtimes.items():
            if not ydl_opts["js_runtimes"].get(rt):
                ydl_opts["js_runtimes"][rt] = rt_dict

    # Add remote components for EJS decryptor
    if "remote_components" not in ydl_opts:
        ydl_opts["remote_components"] = ["ejs:github"]

    # Ensure YouTube player_client and formats
    if "extractor_args" not in ydl_opts:
        ydl_opts["extractor_args"] = {}
    yt_args = ydl_opts["extractor_args"].setdefault("youtube", {})
    if "player_client" not in yt_args or not yt_args["player_client"]:
        yt_args["player_client"] = ["web_embedded", "android", "mweb", "web"]
    elif isinstance(yt_args["player_client"], list) and (len(yt_args["player_client"]) == 0 or yt_args["player_client"][0] in ("ios", "mweb")):
        yt_args["player_client"] = ["web_embedded", "android", "mweb", "web"]
    yt_args.setdefault("formats", ["missing_pot"])

    # Force legacy HTTP handler (urllib) to avoid curl-cffi TLS / OpenSSL DLL conflict on Windows
    if "compat_opts" not in ydl_opts:
        ydl_opts["compat_opts"] = set()
    elif isinstance(ydl_opts["compat_opts"], list):
        ydl_opts["compat_opts"] = set(ydl_opts["compat_opts"])
    ydl_opts["compat_opts"].add("prefer-legacy-http-handler")

    # Enable parallel segment downloads to speed up DASH/HLS downloads
    ydl_opts["concurrent_fragment_downloads"] = 5

    if should_use_impersonate():
        try:
            ydl_opts["impersonate"] = ImpersonateTarget.from_str("chrome")
            logger.info("Automatically added 'chrome' impersonate option to ydl_opts in create_ydl_instance.")
        except Exception as e:
            logger.warning(f"Failed to apply client impersonate settings in create_ydl_instance: {e}")
            
    # Check if a client-specific cookies file exists
    if client_id:
        from utils.cookies import get_cookie_file_path
        client_cookies = get_cookie_file_path(client_id)
        if client_cookies and os.path.exists(client_cookies):
            logger.info(f"Using client-specific cookies for client '{client_id}': {client_cookies}")
            opts = ydl_opts.copy()
            opts["cookiefile"] = client_cookies
            opts.pop("cookiesfrombrowser", None)
            try:
                with open(client_cookies, "r", encoding="utf-8") as f:
                    cookie_content = f.read()
                youtube_cookie_lines = []
                for line in cookie_content.splitlines():
                    if not line.strip().startswith("#") and "youtube.com" in line:
                        parts = line.split("\t")
                        if len(parts) >= 7:
                            masked_val = parts[6][:4] + "..." + parts[6][-4:] if len(parts[6]) > 8 else "..."
                            youtube_cookie_lines.append(f"Domain={parts[0]}, Name={parts[5]}, Expires={parts[4]}, Value={masked_val}")
                logger.info(f"Loaded client cookies for youtube.com (count={len(youtube_cookie_lines)}):")
                for c_log in youtube_cookie_lines:
                    logger.info(f"  [Cookie] {c_log}")
            except Exception as read_err:
                logger.warning(f"Could not print cookies diagnostics: {read_err}")

            try:
                ydl = yt_dlp.YoutubeDL(opts)
                logger.info(f"Successfully loaded yt_dlp with client-specific cookies for: {client_id}")
                return ydl
            except Exception as e:
                logger.warning(f"Failed to load client cookies: {e}")

    # Check if a local cookies.txt file exists in the root folder
    local_cookies = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies.txt")
    if os.path.exists(local_cookies):
        logger.info("Using local default cookies.txt file")
        opts = ydl_opts.copy()
        opts["cookiefile"] = local_cookies
        opts.pop("cookiesfrombrowser", None)
        try:
            return yt_dlp.YoutubeDL(opts)
        except Exception as e:
            logger.warning(f"Failed to load local cookies.txt: {e}")

    if ydl_opts.get("cookiesfrombrowser") != "auto":
        return yt_dlp.YoutubeDL(ydl_opts)
        
    is_headless = os.path.exists('/.dockerenv') or os.environ.get('RENDER') == 'true'
    if is_headless:
        logger.info("Running in headless/Docker/Render environment. Skipping browser cookies search.")
        opts = ydl_opts.copy()
        opts.pop("cookiesfrombrowser", None)
        logger.info("Falling back to YoutubeDL instance without cookies")
        return yt_dlp.YoutubeDL(opts)

    browsers = ["chrome", "edge", "firefox", "opera", "vivaldi", "brave"]
    
    # Filter browsers based on whether their user data directory exists to avoid FileNotFoundError logs
    available_browsers = []
    appdata_local = os.environ.get("LOCALAPPDATA")
    appdata_roaming = os.environ.get("APPDATA")
    
    for browser in browsers:
        exists = False
        if browser == "chrome" and appdata_local:
            exists = os.path.exists(os.path.join(appdata_local, "Google/Chrome/User Data"))
        elif browser == "edge" and appdata_local:
            exists = os.path.exists(os.path.join(appdata_local, "Microsoft/Edge/User Data"))
        elif browser == "brave" and appdata_local:
            exists = os.path.exists(os.path.join(appdata_local, "BraveSoftware/Brave-Browser/User Data"))
        elif browser == "vivaldi" and appdata_local:
            exists = os.path.exists(os.path.join(appdata_local, "Vivaldi/User Data"))
        elif browser == "opera":
            exists = (
                (appdata_roaming and os.path.exists(os.path.join(appdata_roaming, "Opera Software"))) or 
                (appdata_local and os.path.exists(os.path.join(appdata_local, "Opera Software")))
            )
        elif browser == "firefox" and appdata_roaming:
            exists = os.path.exists(os.path.join(appdata_roaming, "Mozilla/Firefox/Profiles"))
        else:
            # Fallback for non-Windows or unknown environments
            exists = True
            
        if exists:
            available_browsers.append(browser)
            
    browsers = available_browsers
    logger.info(f"Available browser cookie sources: {browsers}")

    # Extract target domain for cookie filtering
    target_domain = None
    if url:
        url_lower = url.lower()
        if "facebook" in url_lower or "fb.watch" in url_lower or "fb.gg" in url_lower or "fb.com" in url_lower:
            target_domain = "facebook"
        elif "youtube" in url_lower or "youtu.be" in url_lower:
            target_domain = "youtube"
        elif "instagram" in url_lower:
            target_domain = "instagram"
        elif "tiktok" in url_lower:
            target_domain = "tiktok"

    # Step 1: Prioritize browsers that have cookies for the target domain
    if target_domain:
        for browser in browsers:
            opts = ydl_opts.copy()
            opts["cookiesfrombrowser"] = (browser,)
            try:
                ydl = yt_dlp.YoutubeDL(opts)
                # Force loading of cookiejar and check for domain cookies
                cookiejar = ydl.cookiejar
                if any(target_domain in cookie.domain for cookie in cookiejar):
                    logger.info(f"Successfully loaded cookies from browser: {browser} (matched target domain '{target_domain}')")
                    return ydl
            except Exception:
                pass

    # Step 2: Fallback to the first browser that loads successfully (regardless of domain cookies, skip for YouTube)
    if target_domain != "youtube":
        for browser in browsers:
            opts = ydl_opts.copy()
            opts["cookiesfrombrowser"] = (browser,)
            try:
                ydl = yt_dlp.YoutubeDL(opts)
                _ = ydl.cookiejar
                logger.info(f"Fallback to cookies from browser: {browser}")
                return ydl
            except Exception as e:
                logger.warning(f"Failed to load cookies from browser '{browser}': {e}")
            
    # Step 3: Fallback to no cookies if all failed
    opts = ydl_opts.copy()
    opts.pop("cookiesfrombrowser", None)
    logger.info("Falling back to YoutubeDL instance without cookies")
    return yt_dlp.YoutubeDL(opts)
