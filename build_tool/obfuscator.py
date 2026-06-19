"""
obfuscator.py — Code protection module for EveryThingDownloader

Features (all self-implemented, no PyArmor Pro required):
  1. PyArmor free-tier obfuscation (bytecode level)
  2. IP Lock  — restrict execution to a list of allowed IPs
  3. Date Expiry — refuse to run after a given date
  4. Machine ID Lock — tie the binary to specific hardware fingerprint(s)
  5. String Literal Encoding — base64-encode string constants in source
  6. Variable / function name scrambling (AST-based)
  7. Dead code injection — insert random no-op blocks to confuse reversers
  8. Anti-debug guard — detect debugger and exit
"""

from __future__ import annotations

import ast
import base64
import hashlib
import os
import platform
import random
import re
import shutil
import string
import subprocess
import sys
import textwrap
import uuid
from pathlib import Path
from typing import Optional

# ─── Internal helpers ─────────────────────────────────────────────────────────

def _rand_name(length: int = 12) -> str:
    """Generate a random identifier that looks like a private symbol."""
    prefix = '_' + ''.join(random.choices(string.ascii_lowercase, k=3))
    suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    return prefix + suffix


def _b64_encode_str(s: str) -> str:
    """Return a Python expression that decodes `s` from base64 at runtime."""
    encoded = base64.b64encode(s.encode()).decode()
    return f'__import__("base64").b64decode({repr(encoded)}).decode()'


def _get_machine_id() -> str:
    """Return a stable hardware fingerprint for the current machine."""
    parts = []
    try:
        parts.append(str(uuid.getnode()))          # MAC address
        parts.append(platform.node())              # hostname
        parts.append(platform.processor())         # CPU string
        sys_type = platform.system()
        if sys_type == 'Windows':
            try:
                out = subprocess.check_output(
                    'wmic csproduct get uuid', shell=True, stderr=subprocess.DEVNULL
                ).decode()
                for line in out.splitlines():
                    line = line.strip()
                    if line and line.upper() != 'UUID':
                        parts.append(line)
                        break
            except Exception:
                pass
        elif sys_type == 'Darwin':
            try:
                out = subprocess.check_output(
                    'ioreg -rd1 -c IOPlatformExpertDevice', shell=True, stderr=subprocess.DEVNULL
                ).decode()
                import re
                match = re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', out)
                if match:
                    parts.append(match.group(1))
            except Exception:
                pass
        elif sys_type == 'Linux':
            for path in ['/var/lib/dbus/machine-id', '/etc/machine-id']:
                try:
                    if os.path.exists(path):
                        with open(path, 'r') as f:
                            parts.append(f.read().strip())
                        break
                except Exception:
                    pass
    except Exception:
        pass
    raw = '|'.join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()


# ─── License guard code templates ─────────────────────────────────────────────

_LICENSE_HEADER_TEMPLATE = r'''
# === LICENSE GUARD — DO NOT MODIFY ===
import sys as _sys
import hashlib as _hashlib
import socket as _socket
import platform as _platform
import uuid as _uuid
import datetime as _datetime
import subprocess as _subprocess

def __{fn}_check_license():
    # -- IP check --
    _allowed_ips = {allowed_ips!r}
    _require_ip   = {require_ip!r}

    # -- Date expiry --
    _expiry_date = {expiry_date!r}   # '' means no expiry

    # -- Machine ID lock --
    _allowed_machine_ids = {allowed_machine_ids!r}
    _require_machine_id  = {require_machine_id!r}

    # -- Anti-debug --
    _antidebug = {antidebug!r}

    # ---- anti-debug ----
    if _antidebug:
        try:
            import ctypes
            if hasattr(ctypes, 'windll'):
                if ctypes.windll.kernel32.IsDebuggerPresent():
                    _sys.exit(0)
        except Exception:
            pass
        try:
            import sys
            if sys.gettrace() is not None:
                _sys.exit(0)
        except Exception:
            pass

    # ---- date expiry ----
    if _expiry_date:
        _today = _datetime.datetime.utcnow().strftime('%Y-%m-%d')
        if _today > _expiry_date:
            import tkinter as _tk
            try:
                _r = _tk.Tk(); _r.withdraw()
                _tk.messagebox.showerror(
                    'License Expired',
                    f'This version expired on {{_expiry_date}}.'
                )
                _r.destroy()
            except Exception:
                pass
            _sys.exit(1)

    # ---- IP lock ----
    if _require_ip and _allowed_ips:
        _detected_ips = set()
        try:
            _detected_ips.add(_socket.gethostbyname(_socket.gethostname()))
        except Exception:
            pass
        try:
            _s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
            _s.connect(('8.8.8.8', 80))
            _detected_ips.add(_s.getsockname()[0])
            _s.close()
        except Exception:
            pass
        try:
            import urllib.request as _ur
            _pub = _ur.urlopen('https://api.ipify.org', timeout=4).read().decode()
            _detected_ips.add(_pub.strip())
        except Exception:
            pass
        if not _detected_ips.intersection(_allowed_ips):
            import tkinter as _tk
            try:
                _r = _tk.Tk(); _r.withdraw()
                _tk.messagebox.showerror(
                    'IP Not Allowed',
                    'Your IP address is not authorized to run this software.'
                )
                _r.destroy()
            except Exception:
                pass
            _sys.exit(1)

    # ---- machine ID lock ----
    if _require_machine_id and _allowed_machine_ids:
        def _compute_machine_id():
            _parts = []
            try:
                _parts.append(str(_uuid.getnode()))
                _parts.append(_platform.node())
                _parts.append(_platform.processor())
                _sys_type = _platform.system()
                if _sys_type == 'Windows':
                    try:
                        _out = _subprocess.check_output(
                            'wmic csproduct get uuid', shell=True,
                            stderr=_subprocess.DEVNULL
                        ).decode()
                        for _ln in _out.splitlines():
                            _ln = _ln.strip()
                            if _ln and _ln.upper() != 'UUID':
                                _parts.append(_ln); break
                    except Exception:
                        pass
                elif _sys_type == 'Darwin':
                    try:
                        _out = _subprocess.check_output(
                            'ioreg -rd1 -c IOPlatformExpertDevice', shell=True,
                            stderr=_subprocess.DEVNULL
                        ).decode()
                        import re as _re
                        _match = _re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', _out)
                        if _match:
                            _parts.append(_match.group(1))
                    except Exception:
                        pass
                elif _sys_type == 'Linux':
                    for _path in ['/var/lib/dbus/machine-id', '/etc/machine-id']:
                        try:
                            import os as _os
                            if _os.path.exists(_path):
                                with open(_path, 'r') as _f:
                                    _parts.append(_f.read().strip())
                                break
                        except Exception:
                            pass
            except Exception:
                pass
            return _hashlib.sha256('|'.join(_parts).encode()).hexdigest()

        _mid = _compute_machine_id()
        if _mid not in _allowed_machine_ids:
            import tkinter as _tk
            try:
                _r = _tk.Tk(); _r.withdraw()
                _tk.messagebox.showerror(
                    'Device Not Authorized',
                    'This software is not licensed for this device.'
                )
                _r.destroy()
            except Exception:
                pass
            _sys.exit(1)

__{fn}_check_license()
# === END LICENSE GUARD ===

'''


# ─── AST-based transformer: scramble variable names ───────────────────────────

class _NameScrambler(ast.NodeTransformer):
    """Renames all local variables / private functions in a module."""

    BUILTINS = frozenset(dir(__builtins__) if isinstance(__builtins__, dict)
                         else dir(__builtins__))
    SKIP_PREFIXES = ('__',)

    def __init__(self):
        self._map: dict[str, str] = {}

    def _mapped(self, name: str) -> str:
        if name in self.BUILTINS:
            return name
        if any(name.startswith(p) for p in self.SKIP_PREFIXES):
            return name
        if name not in self._map:
            self._map[name] = _rand_name()
        return self._map[name]

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Load, ast.Del)):
            node.id = self._mapped(node.id)
        return node

    def visit_FunctionDef(self, node):
        if not node.name.startswith('__'):
            node.name = self._mapped(node.name)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        return self.visit_FunctionDef(node)

    def visit_arg(self, node):
        node.arg = self._mapped(node.arg)
        return node


# ─── String literal encoder ───────────────────────────────────────────────────

class _StringEncoder(ast.NodeTransformer):
    """Replace string constants with base64 decode calls."""

    SKIP_PARENTS = (ast.Import, ast.ImportFrom, ast.alias)

    def visit_Constant(self, node):
        if isinstance(node.value, str) and len(node.value) > 4:
            encoded = base64.b64encode(node.value.encode()).decode()
            call = ast.parse(
                f'__import__("base64").b64decode({repr(encoded)}).decode()',
                mode='eval'
            ).body
            return ast.copy_location(call, node)
        return node


# ─── Dead-code injector ───────────────────────────────────────────────────────

_DEAD_CODE_SNIPPETS = [
    'if False:\n    pass\n',
    'for _{v} in range(0):\n    pass\n',
    '_{v} = None; del _{v}\n',
    'try:\n    pass\nexcept Exception:\n    pass\n',
]


def _inject_dead_code(source: str, count: int = 10) -> str:
    lines = source.splitlines(keepends=True)
    positions = random.sample(range(1, max(2, len(lines))), min(count, len(lines) - 1))
    positions.sort(reverse=True)
    for pos in positions:
        snippet = random.choice(_DEAD_CODE_SNIPPETS)
        snippet = snippet.replace('{v}', _rand_name())
        lines.insert(pos, snippet)
    return ''.join(lines)


# ─── Public API ───────────────────────────────────────────────────────────────

class ObfuscationConfig:
    """All configurable protection options."""

    def __init__(self):
        # PyArmor (free tier)
        self.use_pyarmor: bool         = True
        self.pyarmor_obf_code: int     = 1      # 0 = none, 1 = standard, 2 = advanced
        self.pyarmor_mix_str: bool     = True

        # Self-implemented protections
        self.ip_lock: bool             = False
        self.allowed_ips: list[str]    = []

        self.date_expiry: bool         = False
        self.expiry_date: str          = ''     # 'YYYY-MM-DD'

        self.machine_id_lock: bool     = False
        self.allowed_machine_ids: list[str] = []

        self.scramble_names: bool      = True
        self.encode_strings: bool      = True
        self.inject_dead_code: bool    = True
        self.dead_code_count: int      = 15

        self.antidebug: bool           = True

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @staticmethod
    def from_dict(d: dict) -> 'ObfuscationConfig':
        cfg = ObfuscationConfig()
        for k, v in d.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        return cfg


class Obfuscator:
    """Applies all requested protection layers to the project source."""

    def __init__(self, config: ObfuscationConfig):
        self.cfg = config

    # ── Step 1: copy project to a work directory ──────────────────────────────

    def prepare_workdir(self, src_dir: Path, work_dir: Path) -> None:
        if work_dir.exists():
            shutil.rmtree(work_dir)
        shutil.copytree(src_dir, work_dir, ignore=shutil.ignore_patterns(
            '__pycache__', '*.pyc', '.git', 'venv', 'node_modules',
            'dist', 'dist_electron', 'build', '*.egg-info',
            'downloads', 'release', '_pyinstaller_build', 'scratch',
            '_work_obfuscated', '_pyarmor_out',
        ))
        (work_dir / 'downloads').mkdir(exist_ok=True)

    # ── Step 2: inject license guard into app.py ──────────────────────────────

    def inject_license_guard(self, work_dir: Path) -> None:
        app_py = work_dir / 'app.py'
        if not app_py.exists():
            return

        fn_name = _rand_name(8)
        guard = _LICENSE_HEADER_TEMPLATE.format(
            fn=fn_name,
            allowed_ips=self.cfg.allowed_ips,
            require_ip=self.cfg.ip_lock,
            expiry_date=self.cfg.expiry_date if self.cfg.date_expiry else '',
            allowed_machine_ids=self.cfg.allowed_machine_ids,
            require_machine_id=self.cfg.machine_id_lock,
            antidebug=self.cfg.antidebug,
        )

        original = app_py.read_text(encoding='utf-8')
        # Insert after the last top-level import block
        lines = original.splitlines(keepends=True)
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                insert_at = i + 1
        lines.insert(insert_at, guard)
        app_py.write_text(''.join(lines), encoding='utf-8')

    # ── Step 3: AST transformations (scramble names + encode strings) ─────────

    def transform_python_files(self, work_dir: Path) -> None:
        skip_dirs = {
            'venv', 'node_modules', '__pycache__', 'build', 'dist',
            'downloads', 'release', '_pyinstaller_build', 'scratch',
            '_work_obfuscated', '_pyarmor_out',
        }
        for py_file in work_dir.rglob('*.py'):
            # Skip files inside excluded dirs
            if any(p in skip_dirs for p in py_file.parts):
                continue
            try:
                self._transform_file(py_file)
            except Exception as e:
                print(f'  [warn] Could not transform {py_file.name}: {e}')

    def _transform_file(self, py_file: Path) -> None:
        source = py_file.read_text(encoding='utf-8', errors='replace')
        tree   = ast.parse(source, filename=str(py_file))

        if self.cfg.encode_strings:
            tree = _StringEncoder().visit(tree)
            ast.fix_missing_locations(tree)

        if self.cfg.scramble_names:
            tree = _NameScrambler().visit(tree)
            ast.fix_missing_locations(tree)

        new_source = ast.unparse(tree)

        if self.cfg.inject_dead_code:
            new_source = _inject_dead_code(new_source, self.cfg.dead_code_count)

        py_file.write_text(new_source, encoding='utf-8')

    # ── Step 4: PyArmor (free tier) ───────────────────────────────────────────

    def run_pyarmor(self, work_dir: Path, output_dir: Path) -> bool:
        """
        Run PyArmor on the work directory.
        Returns True if successful, False if PyArmor is not installed.
        """
        try:
            subprocess.check_output(['pyarmor', '--version'], stderr=subprocess.STDOUT)
        except (FileNotFoundError, subprocess.CalledProcessError):
            print('  [warn] PyArmor not found — skipping PyArmor obfuscation.')
            return False

        cmd = [
            'pyarmor', 'gen',
            '--output', str(output_dir),
        ]

        if self.cfg.pyarmor_obf_code == 2:
            cmd += ['--obf-code', '2']
        elif self.cfg.pyarmor_obf_code == 0:
            cmd += ['--obf-code', '0']

        if self.cfg.pyarmor_mix_str:
            cmd.append('--mix-str')

        cmd.append(str(work_dir / 'app.py'))

        print('  [pyarmor]', ' '.join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if result.returncode != 0:
            print('  [warn] PyArmor error:', result.stderr[:400])
            return False
        return True

    # ── Main entry ────────────────────────────────────────────────────────────

    def run(
        self,
        src_dir: Path,
        output_dir: Path,
        *,
        progress_cb=None,
    ) -> Path:
        """
        Full obfuscation pipeline.

        Returns the path to the protected source tree ready for packaging.
        """
        def _progress(msg):
            if progress_cb:
                progress_cb(msg)
            else:
                print(msg)

        work_dir = output_dir / '_work_obfuscated'
        _progress('[COPY] Copying source code…')
        self.prepare_workdir(src_dir, work_dir)

        _progress('[LOCK] Injecting License Guard…')
        self.inject_license_guard(work_dir)

        if self.cfg.encode_strings or self.cfg.scramble_names or self.cfg.inject_dead_code:
            _progress('[SCRAMBLE] Applying AST transformations (code scrambling)…')
            self.transform_python_files(work_dir)

        if self.cfg.use_pyarmor:
            _progress('[SHIELD] Running PyArmor…')
            self.run_pyarmor(work_dir, output_dir / '_pyarmor_out')

        _progress('[OK] Protection processing complete.')
        return work_dir


# ─── Utility: get this machine's ID (for UI display) ─────────────────────────

def get_current_machine_id() -> str:
    return _get_machine_id()


# ─── CLI quick-test ───────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('Current Machine ID:', get_current_machine_id())
