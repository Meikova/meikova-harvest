"""
routes/build.py — Build API endpoints for the GUI builder tool

Endpoints:
  GET  /api/machine-id          — Return current machine's hardware fingerprint
  POST /api/build/start         — Start a build job, returns {build_id}
  GET  /api/build/log/<id>      — SSE stream of build log lines
  POST /api/build/cancel        — Cancel running build
"""

from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import uuid
from pathlib import Path

from flask import Blueprint, Response, jsonify, request, stream_with_context

build_bp = Blueprint('build', __name__)

def ensure_vtt_content(text: str) -> str:
    if text and ("<transcript" in text or "<timedtext" in text or text.strip().startswith("<?xml")):
        try:
            import xml.etree.ElementTree as ET
            import html
            root = ET.fromstring(text)
            vtt_lines = ["WEBVTT", ""]
            
            cues = []
            for elem in root.iter():
                if elem.tag in ('text', 'p') and 'start' in elem.attrib:
                    cues.append(elem)
                    
            for idx, child in enumerate(cues):
                start = float(child.attrib.get("start", 0.0))
                dur = float(child.attrib.get("dur", 0.0))
                end = start + dur
                
                def format_time(secs):
                    hrs = int(secs // 3600)
                    mins = int((secs % 3600) // 60)
                    seconds = secs % 60
                    ms = int(round((seconds - int(seconds)) * 1000))
                    return f"{hrs:02d}:{mins:02d}:{int(seconds):02d}.{ms:03d}"
                
                start_str = format_time(start)
                end_str = format_time(end)
                txt = child.text or ""
                txt = html.unescape(txt)
                txt = txt.replace("\n", " ").strip()
                if txt:
                    vtt_lines.append(f"{idx + 1}")
                    vtt_lines.append(f"{start_str} --> {end_str}")
                    vtt_lines.append(txt)
                    vtt_lines.append("")
            if len(vtt_lines) > 2:
                return "\n".join(vtt_lines)
        except Exception:
            pass
    return text

# ── Active build registry ─────────────────────────────────────────────────────
_builds: dict[str, dict] = {}  # build_id → {queue, thread, cancelled}

ROOT_DIR = Path(__file__).resolve().parent.parent

def get_python_executable() -> str:
    """Resolve the python executable, favoring local virtualenv if present."""
    import platform
    is_windows = platform.system().lower().startswith("win")
    if is_windows:
        venv_python = ROOT_DIR / 'venv' / 'Scripts' / 'python.exe'
    else:
        venv_python = ROOT_DIR / 'venv' / 'bin' / 'python'
        
    if venv_python.exists():
        return str(venv_python)
        
    if getattr(sys, 'frozen', False):
        import platform
        return 'python' if platform.system().lower().startswith("win") else 'python3'
        
    return sys.executable


# ─────────────────────────────────────────────────────────────────────────────
# Builder Web GUI Page
# ─────────────────────────────────────────────────────────────────────────────

@build_bp.route('/builder', methods=['GET'])
def builder_gui_page():
    gui_path = ROOT_DIR / 'build_tool' / 'builder_gui.html'
    if gui_path.exists():
        return gui_path.read_text(encoding='utf-8')
    return "Builder GUI file not found.", 404


# ─────────────────────────────────────────────────────────────────────────────
# Machine ID
# ─────────────────────────────────────────────────────────────────────────────

@build_bp.route('/api/machine-id', methods=['GET'])
def get_machine_id():
    try:
        sys.path.insert(0, str(ROOT_DIR))
        from build_tool.obfuscator import get_current_machine_id
        mid = get_current_machine_id()
    except Exception as e:
        mid = f'Error: {e}'
    return jsonify({'machine_id': mid})


@build_bp.route('/api/platform', methods=['GET'])
def get_platform():
    import platform
    return jsonify({
        'platform': platform.system(),
        'node': platform.node(),
        'release': platform.release()
    })


# ─────────────────────────────────────────────────────────────────────────────
# Start build
# ─────────────────────────────────────────────────────────────────────────────

@build_bp.route('/api/build/start', methods=['POST'])
def start_build():
    cfg = request.get_json(force=True, silent=True) or {}
    build_id = str(uuid.uuid4())[:8]

    log_q: queue.Queue = queue.Queue()
    state = {'cancelled': False, 'done': False}
    _builds[build_id] = {'queue': log_q, 'state': state}

    # Build in background thread
    t = threading.Thread(
        target=_run_build,
        args=(build_id, cfg, log_q, state),
        daemon=True,
    )
    t.start()
    _builds[build_id]['thread'] = t

    return jsonify({'build_id': build_id})


def _run_build(build_id: str, cfg: dict, log_q: queue.Queue, state: dict):
    """Run the build process in a background thread, pushing log lines to queue."""

    def push(text: str, level: str = 'dim', done=False, success=False, outputs=None):
        msg = {'text': text, 'level': level}
        if done:
            msg['done']    = True
            msg['success'] = success
            msg['outputs'] = outputs or []
        log_q.put(msg)

    try:
        # Build the CLI command from the config
        target   = cfg.get('target', 'web')
        obf      = cfg.get('obfuscation', {})
        build    = cfg.get('build', {})
        do_obf   = cfg.get('enable_obfuscate', False)

        python_exe = get_python_executable()
        cmd = [python_exe, str(ROOT_DIR / 'build_tool' / 'builder_cli.py')]
        cmd += ['--target', target]
        cmd += ['--name',    build.get('app_name', 'EveryThingDownloader')]
        cmd += ['--version', build.get('version', '1.0.0')]

        platform_choice = cfg.get('platform', 'auto')
        if platform_choice:
            cmd += ['--platform', platform_choice]

        if build.get('company'):
            cmd += ['--company', build['company']]
        if build.get('description'):
            cmd += ['--description', build['description']]
        if build.get('copyright'):
            cmd += ['--copyright', build['copyright']]

        if do_obf:
            cmd.append('--obfuscate')
        if build.get('use_upx'):
            cmd.append('--upx')
        if build.get('console'):
            cmd.append('--console')
        if not obf.get('use_pyarmor', True):
            cmd.append('--no-pyarmor')
        if obf.get('pyarmor_obf_code') is not None:
            cmd += ['--pyarmor-level', str(obf['pyarmor_obf_code'])]
        if not obf.get('pyarmor_mix_str', True):
            cmd.append('--no-pyarmor-mix-str')
        if not obf.get('scramble_names', True):
            cmd.append('--no-scramble')
        if not obf.get('encode_strings', True):
            cmd.append('--no-encode-strings')
        if not obf.get('inject_dead_code', True):
            cmd.append('--no-dead-code')
        if obf.get('dead_code_count') is not None:
            cmd += ['--dead-code-count', str(obf['dead_code_count'])]
        if not obf.get('antidebug', True):
            cmd.append('--no-antidebug')
        if obf.get('ip_lock') and obf.get('allowed_ips'):
            cmd += ['--ip-lock'] + obf['allowed_ips']
        if obf.get('date_expiry') and obf.get('expiry_date'):
            cmd += ['--expire', obf['expiry_date']]
        if obf.get('machine_id_lock'):
            cmd.append('--machine-id')
            if obf.get('allowed_machine_ids'):
                cmd += ['--machine-ids'] + obf['allowed_machine_ids']

        push(f'$ {" ".join(cmd)}', 'dim')
        push('', 'dim')

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            cwd=str(ROOT_DIR),
        )
        _builds[build_id]['proc'] = proc

        import re
        ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

        for line in proc.stdout:
            if state['cancelled']:
                proc.terminate()
                push('[CANCEL] Build cancelled.', 'warn', done=True, success=False)
                return
            line = line.rstrip('\n')
            line = ansi_escape.sub('', line)
            level = 'dim'
            if '[OK' in line or '[SUCCESS]' in line:
                level = 'ok'
            elif '[ERROR]' in line:
                level = 'error'
            elif '[WARN]' in line:
                level = 'warn'
            elif '[INFO]' in line:
                level = 'info'
            push(line, level)

        proc.wait()
        success = proc.returncode == 0

        # Collect output files
        outputs = []
        dirs_to_scan = []
        if target in ('web', 'both'):
            dirs_to_scan.append('dist')
        if target in ('desktop', 'both'):
            dirs_to_scan.append('dist_electron')

        for d in dirs_to_scan:
            dist_dir = ROOT_DIR / d
            if dist_dir.exists():
                for f in dist_dir.iterdir():
                    if f.is_dir():
                        continue
                    if d == 'dist':
                        app_name = cfg.get('build', {}).get('app_name', 'EveryThingDownloader')
                        version = cfg.get('build', {}).get('version', '2.0.0')
                        expected_prefix = f'{app_name}-Web-{version}'
                        if f.name.startswith(expected_prefix):
                            size_mb = f.stat().st_size / 1024 / 1024
                            outputs.append({'path': str(f), 'size': f'{size_mb:.1f} MB'})
                    elif d == 'dist_electron':
                        if f.suffix.lower() in ('.exe', '.msi', '.zip', '.dmg', '.pkg', '.appimage', '.gz', '.deb', '.rpm'):
                            size_mb = f.stat().st_size / 1024 / 1024
                            outputs.append({'path': str(f), 'size': f'{size_mb:.1f} MB'})

        if success:
            push('[SUCCESS] Build completed!', 'ok', done=True, success=True, outputs=outputs)
        else:
            push(f'[ERROR] Build failed (exit code {proc.returncode})', 'error', done=True, success=False)

    except Exception as e:
        push(f'[ERROR] Error: {e}', 'error', done=True, success=False)


# ─────────────────────────────────────────────────────────────────────────────
# Stream log via SSE
# ─────────────────────────────────────────────────────────────────────────────

@build_bp.route('/api/build/log/<build_id>', methods=['GET'])
def stream_log(build_id: str):
    if build_id not in _builds:
        return jsonify({'error': 'Build not found'}), 404

    log_q   = _builds[build_id]['queue']
    state   = _builds[build_id]['state']

    def generate():
        while True:
            try:
                msg = log_q.get(timeout=30)
                yield f'data: {json.dumps(msg)}\n\n'
                if msg.get('done'):
                    state['done'] = True
                    break
            except queue.Empty:
                yield 'data: {"text":".", "level":"dim"}\n\n'

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Cancel build
# ─────────────────────────────────────────────────────────────────────────────

@build_bp.route('/api/build/cancel', methods=['POST'])
def cancel_build():
    # Cancel the most recent running build
    for build_id, info in reversed(list(_builds.items())):
        if not info['state'].get('done'):
            info['state']['cancelled'] = True
            proc = info.get('proc')
            if proc:
                try:
                    proc.terminate()
                except Exception:
                    pass
            return jsonify({'cancelled': True, 'build_id': build_id})
    return jsonify({'cancelled': False, 'message': 'No active build'})


# ─────────────────────────────────────────────────────────────────────────────
# Engine Self-Updater (yt-dlp)
# ─────────────────────────────────────────────────────────────────────────────

@build_bp.route('/api/system/engine-version', methods=['GET'])
def get_engine_version():
    try:
        import yt_dlp
        import importlib
        try:
            importlib.reload(yt_dlp)
        except Exception:
            pass
        version = getattr(yt_dlp, '__version__', None) or getattr(getattr(yt_dlp, 'version', None), '__version__', 'unknown')
        return jsonify({
            'status': 'success',
            'yt_dlp_version': version,
            'is_frozen': getattr(sys, 'frozen', False)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@build_bp.route('/api/system/update-ytdl', methods=['POST'])
def update_ytdl():
    try:
        import yt_dlp
        import importlib
        
        # Run pip upgrade command
        python_exe = get_python_executable()
        cmd = [python_exe, "-m", "pip", "install", "--upgrade", "yt-dlp"]
        # Set creationflags to CREATE_NO_WINDOW on Windows to prevent popups
        kwargs = {}
        if sys.platform.startswith("win"):
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60, **kwargs)
        if res.returncode == 0:
            # Reload module dynamically in the current process
            try:
                importlib.reload(yt_dlp)
                new_version = getattr(yt_dlp, '__version__', None) or getattr(getattr(yt_dlp, 'version', None), '__version__', 'unknown')
            except Exception:
                new_version = "updated (restart recommended)"
            return jsonify({
                'status': 'success',
                'message': 'yt-dlp updated successfully!',
                'output': res.stdout,
                'version': new_version
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to update yt-dlp (exit code {res.returncode})',
                'output': res.stderr or res.stdout
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@build_bp.route('/api/system/translate-sub', methods=['POST'])
def translate_subtitle_endpoint():
    try:
        data = request.get_json(force=True, silent=True) or {}
        url = data.get("url")
        if url and "youtube.com/api/timedtext" in url:
            import re
            if "fmt=" in url:
                url = re.sub(r'fmt=[^&]+', 'fmt=vtt', url)
            else:
                url += "&fmt=vtt" if "?" in url else "?fmt=vtt"
        content = data.get("content")
        target_lang = data.get("target_lang", "vi")
        
        import requests
        import os
        import tempfile
        from utils.ffmpeg import translate_vtt_file
        
        # Write to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".vtt", delete=False, mode="w", encoding="utf-8") as f:
            temp_path = f.name
            
        try:
            if url:
                if url.startswith("/api/download/file/"):
                    # Resolve locally from TEMP_DOWNLOAD_DIR
                    parts = url.split("/")
                    download_id = parts[-1].split("?")[0]
                    from config import TEMP_DOWNLOAD_DIR
                    local_dir = os.path.join(TEMP_DOWNLOAD_DIR, download_id)
                    sub_file = None
                    if os.path.exists(local_dir):
                        for f_name in os.listdir(local_dir):
                            if f_name.endswith(".vtt"):
                                sub_file = os.path.join(local_dir, f_name)
                                break
                    if sub_file and os.path.exists(sub_file):
                        with open(sub_file, "r", encoding="utf-8", errors="ignore") as sf:
                            with open(temp_path, "w", encoding="utf-8") as tf:
                                tf.write(sf.read())
                    else:
                        return jsonify({"status": "error", "message": "Local subtitle file not found"}), 400
                else:
                    resp = requests.get(url, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }, verify=False, timeout=15)
                    if resp.status_code == 200:
                        vtt_text = ensure_vtt_content(resp.text)
                        with open(temp_path, "w", encoding="utf-8") as f:
                            f.write(vtt_text)
                    else:
                        return jsonify({"status": "error", "message": f"Failed to download sub from URL (HTTP {resp.status_code})"}), 400
            elif content:
                vtt_text = ensure_vtt_content(content)
                with open(temp_path, "w", encoding="utf-8") as f:
                    f.write(vtt_text)
            else:
                return jsonify({"status": "error", "message": "Missing url or content"}), 400
                
            # Translate VTT
            translate_vtt_file(temp_path, target_lang=target_lang)
            
            # Read back translated VTT
            with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                translated_vtt = f.read()
                
            return jsonify({
                "status": "success",
                "translated_vtt": translated_vtt
            })
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@build_bp.route('/api/system/proxy-sub', methods=['GET'])
def proxy_subtitle_endpoint():
    url = request.args.get("url")
    if not url:
        return "Missing url parameter", 400
        
    # Auto-normalize old/blocked AnimeVietSub domains to the latest working one
    if url and "animevietsub." in url.lower():
        import re
        url = re.sub(r'animevietsub\.[a-z]+', 'animevietsub.meme', url, flags=re.IGNORECASE)
    # Serve local subtitle/text file directly
    import os
    if os.path.isabs(url) and os.path.isfile(url):
        from utils.security import is_safe_local_media_path
        safe, reason = is_safe_local_media_path(url, allow_user_local_media=True)
        if not safe:
            return f"Security restriction: {reason}", 403
        try:
            with open(url, 'r', encoding='utf-8', errors='ignore') as local_f:
                text = local_f.read()
            from flask import make_response
            resp = make_response(text)
            ext = url.rsplit('.', 1)[-1].lower() if '.' in url else ''
            if ext == 'vtt':
                resp.headers['Content-Type'] = 'text/vtt; charset=utf-8'
            elif ext in ('html', 'htm'):
                resp.headers['Content-Type'] = 'text/html; charset=utf-8'
            else:
                resp.headers['Content-Type'] = 'text/plain; charset=utf-8'
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return resp
        except Exception as e:
            return f"Error reading local file: {e}", 500
    
    mode = request.args.get("mode", "vtt").lower()
    client_id = request.args.get("client_id")
    
    if "youtube.com/api/timedtext" in url and mode == "vtt":
        import re
        if "fmt=" in url:
            url = re.sub(r'fmt=[^&]+', 'fmt=vtt', url)
        else:
            url += "&fmt=vtt" if "?" in url else "?fmt=vtt"
    try:
        from flask import make_response
        import os
        from config import TEMP_DOWNLOAD_DIR
        
        text = ""
        # Resolve local file if URL is local download stream
        if url.startswith("/api/download/file/"):
            parts = url.split("/")
            download_id = parts[-1].split("?")[0]
            local_dir = os.path.join(TEMP_DOWNLOAD_DIR, download_id)
            sub_file = None
            if os.path.exists(local_dir):
                for f_name in os.listdir(local_dir):
                    if f_name.endswith(".vtt") or (mode == "html" and (f_name.endswith(".html") or f_name.endswith(".htm"))):
                        sub_file = os.path.join(local_dir, f_name)
                        break
            if sub_file and os.path.exists(sub_file):
                with open(sub_file, "r", encoding="utf-8", errors="ignore") as sf:
                    text = sf.read()
            else:
                return "Local file not found", 404
        elif os.path.isabs(url) and os.path.isfile(url):
            with open(url, "r", encoding="utf-8", errors="ignore") as sf:
                text = sf.read()
        else:
            # External URL proxying
            from utils.security import is_safe_remote_url
            safe, reason = is_safe_remote_url(url)
            if not safe:
                return f"Security restriction: {reason}", 403

            if "googleapiscdn.com/player/" in url and "isFinal=" not in url:
                url += ("&" if "?" in url else "?") + "isFinal=1"
            # Get user cookies if available
            cookies_dict = {}
            if client_id:
                from utils.cookies import get_cookie_file_path
                client_cookies = get_cookie_file_path(client_id)
                if client_cookies and os.path.exists(client_cookies):
                    try:
                        with open(client_cookies, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                line = line.strip()
                                if not line or line.startswith('#'):
                                    continue
                                parts = line.split('\t')
                                if len(parts) >= 7:
                                    cookies_dict[parts[5]] = parts[6]
                    except Exception as cookie_err:
                        # Log or pass
                        pass
            
            from extractors.generic import fetch_html
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            from utils.helpers import get_referer_by_url
            custom_referer = request.args.get("referer")
            referer = custom_referer or get_referer_by_url(url)
            if "googleapiscdn.com" in url:
                if referer and ("animevietsub" in referer or referer.startswith("http")):
                    headers["Referer"] = referer if referer.endswith("/") else referer + "/"
                else:
                    headers["Referer"] = "https://animevietsub.nl/"
                headers["Origin"] = "https://storage.googleapiscdn.com"
            elif referer:
                headers["Referer"] = referer
            html_content = fetch_html(url, headers=headers, cookies=cookies_dict)
            if html_content:
                text = html_content
            else:
                # Fallback to requests
                import requests
                resp = requests.get(url, headers=headers, cookies=cookies_dict, verify=False, timeout=15)
                text = resp.text
        
        if mode == "vtt":
            text = ensure_vtt_content(text)
            content_type = "text/vtt; charset=utf-8"
        elif mode == "html":
            content_type = "text/html; charset=utf-8"
            # Inject overrides for AVS and RoPhim player pages to prevent devtools redirect and environment blockage
            if (("googleapiscdn.com" in url or "_avsExpV" in text) or ("rophim.stream" in url or "data-cfg" in text) or ("createShield" in text)):
                import re
                # 1. Base href for googleapiscdn to resolve relative assets cleanly
                if "googleapiscdn.com" in url and "<base" not in text.lower():
                    text = text.replace("<head>", '<head><base href="https://storage.googleapiscdn.com/">', 1)

                # 3. Disable showFallback banner call
                text = text.replace("function showFallback", "function showFallback_disabled")

                # 4. Remove ALL references to devtools-warning from the HTML
                text = text.replace('devtools-warning', 'devtools-blocked-noop')
                # 5. Remove Cloudflare challenge script that creates hidden iframes
                text = re.sub(
                    r'<script>\(function\(\)\{function c\(\).*?challenge-platform.*?</script>',
                    '', text, flags=re.DOTALL
                )
                # 6. Remove the Cloudflare beacon script
                text = re.sub(
                    r'<script defer src="https://static\.cloudflareinsights\.com/beacon\.min\.js.*?</script>',
                    '', text, flags=re.DOTALL
                )
                # 4. Inject script to neutralize devtools detection methods and hook MSE
                inject_script = """<script data-cfasync="false">
(function(){
    var _realParent = (typeof window !== 'undefined' && window.parent && window.parent !== window) ? window.parent : null;
    const noop = function() {};
    const methods = [
        'log', 'warn', 'error', 'info', 'debug', 'clear', 'table', 'dir', 'dirxml',
        'trace', 'group', 'groupCollapsed', 'groupEnd', 'time', 'timeEnd', 'timeLog',
        'count', 'countReset', 'assert', 'profile', 'profileEnd'
    ];
    methods.forEach(function(method) {
        try {
            console[method] = noop;
        } catch(e) {}
    });

    // 2. Override top, parent, outerWidth and outerHeight to match innerWidth and innerHeight
    // This neutralizes iframe embedding anti-tamper checks and window-size difference devtools detection
    try {
        Object.defineProperty(window, 'top', {
            get: function() { return window; },
            configurable: true
        });
        Object.defineProperty(window, 'parent', {
            get: function() { return window; },
            configurable: true
        });
    } catch(e) {}

    [window].forEach(function(w) {
        try {
            if (w) {
                Object.defineProperty(w, 'outerWidth', {
                    get: function() { return window.innerWidth; },
                    configurable: true
                });
                Object.defineProperty(w, 'outerHeight', {
                    get: function() { return window.innerHeight; },
                    configurable: true
                });
            }
        } catch(e) {}
    });

    // 1. Spoof Navigator User-Agent and AppVersion to avoid Electron incompatibility detection
    try {
        Object.defineProperty(navigator, 'userAgent', {
            get: function() { return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'; },
            configurable: true
        });
        Object.defineProperty(navigator, 'appVersion', {
            get: function() { return '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'; },
            configurable: true
        });
    } catch(e) {}

    // Neutralize F12 and inspection key events inside iframe
    try {
        window.addEventListener('keydown', function(e) {
            if (e.keyCode === 123 || (e.ctrlKey && e.shiftKey && (e.keyCode === 73 || e.keyCode === 74 || e.keyCode === 67)) || (e.ctrlKey && e.keyCode === 85)) {
                e.stopImmediatePropagation();
                e.preventDefault();
            }
        }, true);
    } catch(e) {}

    // Neutralize anti-iframe blackout CSS rules dynamically, hide fallback banners, and eradicate ads via pure CSS
    try {
        const injectUnblockCss = function() {
            if (!document.getElementById('avs-unblock-style')) {
                const style = document.createElement('style');
                style.id = 'avs-unblock-style';
                style.textContent = 'html, body { visibility: visible !important; opacity: 1 !important; display: block !important; } body::before, body::after { display: none !important; content: none !important; visibility: hidden !important; } #avs-pause-ad, .avs-pause-ad, [id*="pause-ad"], [class*="pause-ad"], [id*="avs-pause"], [class*="avs-pause"], .avs-pause-ad-box, .avs-pause-ad-link, .avs-pause-ad-img, .avs-pause-ad-label, .avs-pause-ad-actions, .avs-pause-ad-dismiss, .avs-pause-ad-resume, #avs-resume-overlay, #avs-resume-box, .avs-resume-box, [id*="avs-resume"], [class*="avs-resume"], #avs-compat-fallback, .avs-warning, .browser-warning, [id*="compat-fallback"], .quality-notice, [class*="ads"], [id*="ads"], [class*="banner"], [id*="banner"], [id*="devtools"], [class*="devtools"], [id*="adblock"], [class*="adblock"], .avs-ads, #avs-ads, .vast-skip-button, .jw-ad-container, iframe[src*="ad"], iframe[src*="bet"], a[href*="bom88"], a[href*="bet"] { display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; height: 0 !important; width: 0 !important; max-height: 0 !important; max-width: 0 !important; overflow: hidden !important; }';
                (document.head || document.documentElement).appendChild(style);
            }
        };
        injectUnblockCss();
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', injectUnblockCss);
        }
    } catch(e) {}

    // 3. Override Location prototype to intercept devtools-warning redirect and reload loops
    try {
        Location.prototype.reload = function() {};
        const origReplace = Location.prototype.replace;
        Location.prototype.replace = function(url) {
            if (typeof url === 'string' && (url.includes('devtools') || url.includes('warning') || url.includes('blocked'))) {
                return;
            }
            return;
        };
        const origAssign = Location.prototype.assign;
        Location.prototype.assign = function(url) {
            if (typeof url === 'string' && (url.includes('devtools') || url.includes('warning') || url.includes('blocked'))) {
                return;
            }
            return;
        };
        const desc = Object.getOwnPropertyDescriptor(Location.prototype, 'href');
        if (desc && desc.set) {
            Object.defineProperty(Location.prototype, 'href', {
                set: function(url) {
                    if (typeof url === 'string' && (url.includes('devtools') || url.includes('warning') || url.includes('blocked'))) {
                        return;
                    }
                    return;
                },
                configurable: true
            });
        }
    } catch(e) {}

    // 4. Neutralize debugger-based devtools detection (both interval and timeout)
    var _origSetInterval = window.setInterval;
    window.setInterval = function(fn, delay) {
        var fnStr = (typeof fn === 'function') ? fn.toString() : String(fn);
        if (fnStr.indexOf('debugger') !== -1) {
            return _origSetInterval(function(){}, 99999);
        }
        return _origSetInterval.apply(this, arguments);
    };
    var _origSetTimeout = window.setTimeout;
    window.setTimeout = function(fn, delay) {
        var fnStr = (typeof fn === 'function') ? fn.toString() : String(fn);
        if (fnStr.indexOf('debugger') !== -1) {
            return _origSetTimeout(function(){}, 99999);
        }
        return _origSetTimeout.apply(this, arguments);
    };
    var _origEval = window.eval;
    window.eval = function(code) {
        if (typeof code === 'string' && code.indexOf('debugger') !== -1) {
            return undefined;
        }
        return _origEval.apply(this, arguments);
    };
    var _origFunction = window.Function;
    var FunctionHandler = function(...args) {
        if (args.length > 0) {
            var body = args[args.length - 1];
            if (typeof body === 'string' && body.indexOf('debugger') !== -1) {
                args[args.length - 1] = body.replace(/debugger/g, '');
            }
        }
        if (new.target) {
            return Reflect.construct(_origFunction, args, new.target);
        }
        return _origFunction.apply(this, args);
    };
    FunctionHandler.prototype = _origFunction.prototype;
    window.Function = FunctionHandler;

    // 5. Mock service worker registration with valid registration object to satisfy callbacks
    if (navigator.serviceWorker) {
        navigator.serviceWorker.register = function() {
            return Promise.resolve({
                active: { postMessage: function() {}, state: 'activated' },
                installing: null,
                waiting: null,
                scope: '/',
                addEventListener: function() {},
                removeEventListener: function() {}
            });
        };
    }

    // 6. JWPlayer auto-play trigger
    var _playTriggerTimer = setInterval(function() {
        try {
            if (typeof jwplayer === 'function') {
                var p = jwplayer('player');
                if (p && typeof p.play === 'function') {
                    var s = p.getState ? p.getState() : '';
                    if (s === 'idle' || s === 'paused') {
                        p.play();
                    }
                }
            }
        } catch(e) {}
    }, 1000);
    setTimeout(function() { clearInterval(_playTriggerTimer); }, 15000);

    // 7. Hook MSE SourceBuffer.prototype.appendBuffer to capture streaming media chunks
    try {
        if (typeof window.SourceBuffer !== 'undefined' && !window._mseAppendHooked) {
            window._mseAppendHooked = true;
            window._capturedMediaChunks = [];
            var origAppend = SourceBuffer.prototype.appendBuffer;
            SourceBuffer.prototype.appendBuffer = function(buf) {
                try {
                    if (buf) {
                        var chunk = buf.slice ? buf.slice(0) : new Uint8Array(buf).buffer;
                        window._capturedMediaChunks.push(chunk);
                        var targetParent = (_realParent && _realParent !== window) ? _realParent : ((window.parent && window.parent !== window) ? window.parent : null);
                        if (targetParent) {
                            targetParent.postMessage({
                                type: 'MSE_CHUNK_CAPTURED',
                                totalChunks: window._capturedMediaChunks.length,
                                totalBytes: window._capturedMediaChunks.reduce(function(a, b){ return a + b.byteLength; }, 0)
                            }, '*');
                        }
                    }
                } catch(err) {}
                return origAppend.apply(this, arguments);
            };
            window.getCapturedStreamBlob = function(mimeType) {
                return new Blob(window._capturedMediaChunks, { type: mimeType || 'video/mp4' });
            };
        }
    } catch(e) {}

    // 8. Auto-stream fast buffer acceleration
    if (window.location.search.indexOf('auto_stream=1') !== -1) {
        var _fastBufferTimer = setInterval(function() {
            try {
                if (typeof jwplayer === 'function') {
                    var p = jwplayer('player');
                    if (p) {
                        if (typeof p.setMute === 'function') p.setMute(true);
                        var s = p.getState ? p.getState() : '';
                        if (s === 'idle' || s === 'paused') p.play();
                    }
                }
                var v = document.querySelector('video');
                if (v) {
                    v.muted = true;
                    v.playbackRate = 16.0;
                    if (v.paused) v.play().catch(function(){});
                }
            } catch(e) {}
        }, 500);
        setTimeout(function() { clearInterval(_fastBufferTimer); }, 180000);
    }

    try {
        document.addEventListener('ended', function() {
            var targetParent = (_realParent && _realParent !== window) ? _realParent : ((window.parent && window.parent !== window) ? window.parent : null);
            if (targetParent) {
                targetParent.postMessage({ type: 'MSE_STREAM_COMPLETE' }, '*');
            }
        }, true);
    } catch(e) {}
})();
</script>"""
                text = text.replace('<head>', '<head>' + inject_script, 1)
                text = text.replace("window._avsDomains = [", "window._avsDomains = [[49,50,55,46,48,46,48,46,49],")
                text = text.replace("function _avsShowBrowserUpgradeNotice(){", "function _avsShowBrowserUpgradeNotice(){return;")
                text = text.replace("function _runCompatBootstrap(){", "function _runCompatBootstrap(){try{if(typeof startPlayer==='function')startPlayer();}catch(e){};return;")
        else:
            content_type = "text/plain; charset=utf-8"
            
        response = make_response(text)
        response.headers["Content-Type"] = content_type
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response
    except Exception as e:
        return str(e), 500


@build_bp.route('/api/build/config', methods=['GET'])
def get_build_config():
    import sqlite3
    from config import DB_PATH
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS build_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        cursor.execute("SELECT value FROM build_settings WHERE key = 'last_config'")
        row = cursor.fetchone()
        conn.close()
        if row:
            return jsonify(json.loads(row[0]))
        return jsonify({})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@build_bp.route('/api/build/config', methods=['POST'])
def save_build_config():
    import sqlite3
    from config import DB_PATH
    try:
        config_data = request.json
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS build_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        cursor.execute(
            "INSERT INTO build_settings (key, value) VALUES ('last_config', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = ?",
            (json.dumps(config_data), json.dumps(config_data))
        )
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Configuration saved successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# Publish Git Release (Tag & Push to GitHub)
# ─────────────────────────────────────────────────────────────────────────────

@build_bp.route('/api/build/publish', methods=['POST'])
def publish_build():
    cfg = request.get_json(force=True, silent=True) or {}
    build_id = str(uuid.uuid4())[:8]

    log_q = queue.Queue()
    state = {'cancelled': False, 'done': False}
    _builds[build_id] = {'queue': log_q, 'state': state}

    version = cfg.get('build', {}).get('version', '1.0.0')
    app_name = cfg.get('build', {}).get('app_name', 'EveryThingDownloader')

    pub_cfg = cfg.get('publish', {})
    tag = pub_cfg.get('tag')
    commit_msg = pub_cfg.get('commit_msg')
    changelog = pub_cfg.get('changelog')

    # Run git release in background thread
    t = threading.Thread(
        target=_run_publish,
        args=(build_id, version, app_name, tag, commit_msg, changelog, log_q, state),
        daemon=True,
    )
    t.start()
    _builds[build_id]['thread'] = t

    return jsonify({'build_id': build_id})


def _run_publish(build_id: str, version: str, app_name: str, tag: str | None, commit_msg: str | None, changelog: str | None, log_q: queue.Queue, state: dict):
    def push(text: str, level: str = 'dim', done=False, success=False):
        msg = {'text': text, 'level': level}
        if done:
            msg['done']    = True
            msg['success'] = success
        log_q.put(msg)

    try:
        import importlib
        import build_tool.git_helper
        importlib.reload(build_tool.git_helper)
        from build_tool.git_helper import publish_git_release
        
        def progress_cb(msg, level):
            push(msg, level)

        success = publish_git_release(
            ROOT_DIR,
            version=version,
            app_name=app_name,
            tag=tag,
            commit_msg=commit_msg,
            changelog=changelog,
            progress_cb=progress_cb
        )
        if success:
            push('[SUCCESS] Git publication complete! GitHub Actions will now build the release in the cloud.', 'ok', done=True, success=True)
        else:
            push('[ERROR] Git publication failed. Check console log above.', 'error', done=True, success=False)
    except Exception as e:
        push(f'[ERROR] Error: {e}', 'error', done=True, success=False)


# Anti-devtools redirect: return blank page so iframe is not navigated away
@build_bp.route('/devtools-warning', methods=['GET'])
def devtools_warning_stub():
    from flask import make_response
    r = make_response('<html><body></body></html>', 200)
    r.headers['Content-Type'] = 'text/html; charset=utf-8'
    return r

# Service worker stub: player requests /sw.js, return empty JS
@build_bp.route('/sw.js', methods=['GET'])
def sw_js_stub():
    from flask import make_response
    r = make_response('// no-op service worker', 200)
    r.headers['Content-Type'] = 'application/javascript; charset=utf-8'
    return r

# Transparent Reverse Proxy for Google CDN static assets
@build_bp.route('/static/jwplayer/<path:filename>', methods=['GET', 'HEAD'])
def proxy_jwplayer_static(filename):
    import requests
    target_url = f"https://storage.googleapiscdn.com/static/jwplayer/{filename}"
    if request.query_string:
        target_url += f"?{request.query_string.decode('utf-8')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://animevietsub.love/"
    }
    try:
        resp = requests.get(target_url, headers=headers, verify=False, timeout=10)
        from flask import make_response
        r = make_response(resp.content, resp.status_code)
        if "Content-Type" in resp.headers:
            r.headers["Content-Type"] = resp.headers["Content-Type"]
        r.headers["Access-Control-Allow-Origin"] = "*"
        return r
    except Exception as e:
        return str(e), 500


@build_bp.route('/static/wp-player/<path:filename>', methods=['GET', 'HEAD'])
def proxy_wpplayer_static(filename):
    import requests
    target_url = f"https://storage.googleapiscdn.com/static/wp-player/{filename}"
    if request.query_string:
        target_url += f"?{request.query_string.decode('utf-8')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://animevietsub.love/"
    }
    try:
        resp = requests.get(target_url, headers=headers, verify=False, timeout=10)
        from flask import make_response
        r = make_response(resp.content, resp.status_code)
        if "Content-Type" in resp.headers:
            r.headers["Content-Type"] = resp.headers["Content-Type"]
        r.headers["Access-Control-Allow-Origin"] = "*"
        return r
    except Exception as e:
        return str(e), 500


@build_bp.route('/static/<filename>', methods=['GET', 'HEAD'])
def proxy_avs_main_static(filename):
    avs_files = [
        "avs-shield.min.js",
        "avs-loader.min.js",
        "avs-fingerprint.min.js",
        "init.min.js",
        "pako.min.js",
        "jquery-3.7.1.min.js",
        "style.css"
    ]
    if filename in avs_files:
        import requests
        target_url = f"https://storage.googleapiscdn.com/static/{filename}"
        if request.query_string:
            target_url += f"?{request.query_string.decode('utf-8')}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://animevietsub.love/"
        }
        try:
            resp = requests.get(target_url, headers=headers, verify=False, timeout=10)
            content = resp.content
            if filename.endswith(".js"):
                try:
                    text_content = content.decode("utf-8", errors="ignore")
                    text_content = text_content.replace("devtools-warning", "devtools-blocked-noop")
                    # Neutralize static debugger statements completely
                    text_content = text_content.replace("debugger", "/* debugger neutralized */")
                    if filename == "init.min.js":
                        text_content = text_content.replace("function _avsShowBrowserUpgradeNotice(){", "function _avsShowBrowserUpgradeNotice(){return;")
                        text_content = text_content.replace("function _runCompatBootstrap(){", "function _runCompatBootstrap(){try{if(typeof startPlayer==='function')startPlayer();}catch(e){};return;")
                    content = text_content.encode("utf-8")
                except Exception:
                    pass
            from flask import make_response
            r = make_response(content, resp.status_code)
            if "Content-Type" in resp.headers:
                r.headers["Content-Type"] = resp.headers["Content-Type"]
            r.headers["Access-Control-Allow-Origin"] = "*"
            return r
        except Exception as e:
            return str(e), 500
            
    # Serve local files
    from flask import send_from_directory
    import os
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
    return send_from_directory(static_dir, filename)


@build_bp.route('/playlist/<path:filename>', methods=['GET'])
def proxy_playlist(filename):
    import requests
    target_url = f"https://storage.googleapiscdn.com/playlist/{filename}"
    if request.query_string:
        target_url += f"?{request.query_string.decode('utf-8')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://animevietsub.love/"
    }
    try:
        resp = requests.get(target_url, headers=headers, verify=False, timeout=10)
        content = resp.content
        # Do not rewrite chunk or seg-key URLs - Electron has webSecurity: false and fetches directly from CDN with valid TLS fingerprint
        from flask import make_response
        r = make_response(content, resp.status_code)
        for k, v in resp.headers.items():
            if k.lower() not in ('content-encoding', 'content-length', 'transfer-encoding', 'connection'):
                r.headers[k] = v
        r.headers["Access-Control-Allow-Origin"] = "*"
        r.headers["Access-Control-Expose-Headers"] = "*"
        return r
    except Exception as e:
        return str(e), 500


@build_bp.route('/chunks/<path:filename>', methods=['GET'])
def proxy_chunks(filename):
    import requests
    target_url = f"https://storage.googleapiscdn.com/chunks/{filename}"
    if request.query_string:
        target_url += f"?{request.query_string.decode('utf-8')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://storage.googleapiscdn.com/"
    }
    try:
        resp = requests.get(target_url, headers=headers, verify=False, timeout=15)
        from flask import make_response
        r = make_response(resp.content, resp.status_code)
        if "Content-Type" in resp.headers:
            r.headers["Content-Type"] = resp.headers["Content-Type"]
        r.headers["Access-Control-Allow-Origin"] = "*"
        return r
    except Exception as e:
        return str(e), 500


@build_bp.route('/seg-key/<path:filename>', methods=['GET'])
def proxy_seg_key(filename):
    import requests
    target_url = f"https://storage.googleapiscdn.com/seg-key/{filename}"
    if request.query_string:
        target_url += f"?{request.query_string.decode('utf-8')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://storage.googleapiscdn.com/"
    }
    try:
        resp = requests.get(target_url, headers=headers, verify=False, timeout=10)
        from flask import make_response
        r = make_response(resp.content, resp.status_code)
        if "Content-Type" in resp.headers:
            r.headers["Content-Type"] = resp.headers["Content-Type"]
        r.headers["Access-Control-Allow-Origin"] = "*"
        return r
    except Exception as e:
        return str(e), 500


@build_bp.route('/status/<path:filename>', methods=['GET'])
def proxy_status_api(filename):
    import requests
    target_url = f"https://storage.googleapiscdn.com/status/{filename}"
    if request.query_string:
        target_url += f"?{request.query_string.decode('utf-8')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://animevietsub.love/"
    }
    try:
        resp = requests.get(target_url, headers=headers, verify=False, timeout=10)
        from flask import make_response
        r = make_response(resp.content, resp.status_code)
        if "Content-Type" in resp.headers:
            r.headers["Content-Type"] = resp.headers["Content-Type"]
        r.headers["Access-Control-Allow-Origin"] = "*"
        return r
    except Exception as e:
        return str(e), 500


@build_bp.route('/admin/api/ads/active', methods=['GET', 'POST', 'HEAD', 'OPTIONS'])
@build_bp.route('/ads/active', methods=['GET', 'POST', 'HEAD', 'OPTIONS'])
def proxy_ads_active_api():
    from flask import jsonify, make_response
    if request.method == 'OPTIONS':
        r = make_response('', 204)
        r.headers["Access-Control-Allow-Origin"] = "*"
        r.headers["Access-Control-Allow-Methods"] = "GET, POST, HEAD, OPTIONS"
        r.headers["Access-Control-Allow-Headers"] = "*"
        return r
    resp = jsonify({"pauseAd": None, "ads": []})
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp
