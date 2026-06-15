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

# ── Active build registry ─────────────────────────────────────────────────────
_builds: dict[str, dict] = {}  # build_id → {queue, thread, cancelled}

ROOT_DIR = Path(__file__).resolve().parent.parent

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

        cmd = [sys.executable, str(ROOT_DIR / 'build_tool' / 'builder_cli.py')]
        cmd += ['--target', target]
        cmd += ['--name',    build.get('app_name', 'EveryThingDownloader')]
        cmd += ['--version', build.get('version', '1.0.0')]

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

        for d in dirs_to_scan:
            dist_dir = ROOT_DIR / d
            if dist_dir.exists():
                for f in dist_dir.glob('*.exe'):
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
