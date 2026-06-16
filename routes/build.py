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
        return 'python'
        
    return sys.executable


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
        if not obf.get('scramble_names', True):
            cmd.append('--no-scramble')
        if not obf.get('encode_strings', True):
            cmd.append('--no-encode-strings')
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

        import platform
        is_windows = (platform.system() == 'Windows')

        for d in dirs_to_scan:
            dist_dir = ROOT_DIR / d
            if dist_dir.exists():
                for f in dist_dir.iterdir():
                    if f.is_dir():
                        continue
                    if is_windows:
                        if f.suffix.lower() == '.exe':
                            size_mb = f.stat().st_size / 1024 / 1024
                            outputs.append({'path': str(f), 'size': f'{size_mb:.1f} MB'})
                    else:
                        if d == 'dist':
                            app_name = cfg.get('build', {}).get('app_name', 'EveryThingDownloader')
                            if f.name == app_name:
                                size_mb = f.stat().st_size / 1024 / 1024
                                outputs.append({'path': str(f), 'size': f'{size_mb:.1f} MB'})
                        elif d == 'dist_electron':
                            if f.suffix.lower() in ('.dmg', '.zip'):
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
        else:
            # External URL proxying
            # Get user cookies if available
            cookies_dict = {}
            if client_id:
                client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")
                if os.path.exists(client_cookies):
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

    # Run git release in background thread
    t = threading.Thread(
        target=_run_publish,
        args=(build_id, version, log_q, state),
        daemon=True,
    )
    t.start()
    _builds[build_id]['thread'] = t

    return jsonify({'build_id': build_id})


def _run_publish(build_id: str, version: str, log_q: queue.Queue, state: dict):
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

        success = publish_git_release(ROOT_DIR, version, progress_cb=progress_cb)
        if success:
            push('[SUCCESS] Git publication complete! GitHub Actions will now build the release in the cloud.', 'ok', done=True, success=True)
        else:
            push('[ERROR] Git publication failed. Check console log above.', 'error', done=True, success=False)
    except Exception as e:
        push(f'[ERROR] Error: {e}', 'error', done=True, success=False)



