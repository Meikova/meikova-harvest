"""
packager.py — Build pipeline for EveryThingDownloader

Outputs:
  1. dist/EveryThingDownloader-Web.exe     — Standalone Flask server exe
  2. dist_electron/EveryThingDownloader-Setup.exe  — Full Electron desktop installer
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────

ROOT_DIR     = Path(__file__).resolve().parent.parent
BUILD_TOOL   = Path(__file__).resolve().parent
ELECTRON_DIR = ROOT_DIR / 'electron'
DIST_DIR     = ROOT_DIR / 'dist'
DIST_ELECTRON = ROOT_DIR / 'dist_electron'
RESOURCES_DIR = ELECTRON_DIR / 'resources'

# ─── PyInstaller spec template ────────────────────────────────────────────────

PYINSTALLER_SPEC = '''\
# -*- mode: python ; coding: utf-8 -*-
import sys, os

block_cipher = None

a = Analysis(
    ['{entry_point}'],
    pathex=['{root_dir}'],
    binaries=[],
    datas=[
        ('{root_dir}/static', 'static'),
        ('{root_dir}/templates', 'templates'),
        ('{root_dir}/downloads', 'downloads'),
        ('{root_dir}/config.py', '.'),
    ],
    hiddenimports=[
        'flask', 'flask_cors', 'yt_dlp', 'gallery_dl',
        'static_ffmpeg', 'curl_cffi', 'quickjs',
        'routes', 'routes.pages', 'routes.info',
        'routes.download', 'routes.cookies',
        'extractors', 'utils',
        'engineio', 'socketio',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{app_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx={use_upx},
    upx_exclude=[],
    runtime_tmpdir=None,
    console={console},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    {icon_line}
    {version_line}
)
'''

# ─── Version info file (Windows .exe metadata) ───────────────────────────────

VERSION_INFO_TEMPLATE = '''\
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, 0),
    prodvers=({major}, {minor}, {patch}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{company}'),
         StringStruct(u'FileDescription', u'{description}'),
         StringStruct(u'FileVersion', u'{version}'),
         StringStruct(u'InternalName', u'{name}'),
         StringStruct(u'LegalCopyright', u'{copyright}'),
         StringStruct(u'OriginalFilename', u'{name}.exe'),
         StringStruct(u'ProductName', u'{product}'),
         StringStruct(u'ProductVersion', u'{version}')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [0x0409, 1200])])
  ]
)
'''


class BuildConfig:
    def __init__(self):
        self.app_name:    str  = 'EveryThingDownloader'
        self.version:     str  = '1.0.0'
        self.company:     str  = 'EveryThingDownloader'
        self.description: str  = 'EveryThingDownloader'
        self.copyright:   str  = f'© 2026 EveryThingDownloader'
        self.icon_path:   str  = str(ELECTRON_DIR / 'resources' / 'icon.ico')
        self.use_upx:     bool = False    # UPX compression (reduces size but slower start)
        self.console:     bool = False    # False = no console window in production

        # Protected source directory (set by Obfuscator)
        self.protected_src: Path | None = None

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        if isinstance(d.get('protected_src'), Path):
            d['protected_src'] = str(d['protected_src'])
        return d

    @staticmethod
    def from_dict(d: dict) -> 'BuildConfig':
        cfg = BuildConfig()
        for k, v in d.items():
            if hasattr(cfg, k):
                setattr(cfg, k, Path(v) if k == 'protected_src' and v else v)
        return cfg


class Packager:
    """Orchestrates PyInstaller (web exe) and electron-builder (desktop exe)."""

    def __init__(self, config: BuildConfig):
        self.cfg = config

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _progress(self, msg: str, cb=None):
        if cb:
            cb(msg)
        else:
            print(msg)

    def _version_tuple(self):
        parts = self.cfg.version.split('.')
        parts += ['0'] * (3 - len(parts))
        return tuple(int(x) for x in parts[:3])

    def _write_version_info(self, build_dir: Path) -> Path:
        major, minor, patch = self._version_tuple()
        content = VERSION_INFO_TEMPLATE.format(
            major=major, minor=minor, patch=patch,
            company=self.cfg.company,
            description=self.cfg.description,
            version=self.cfg.version,
            name=self.cfg.app_name,
            copyright=self.cfg.copyright,
            product=self.cfg.app_name,
        )
        vf = build_dir / 'version_info.txt'
        vf.write_text(content, encoding='utf-8')
        return vf

    def _write_spec(self, entry_point: Path, build_dir: Path, version_file: Path) -> Path:
        icon = Path(self.cfg.icon_path) if self.cfg.icon_path else Path('')
        src_root = entry_point.parent

        if platform.system() == 'Windows':
            icon_line = f"icon='{str(icon).replace('\\', '/')}'," if icon else "icon=None,"
            version_line = f"version='{str(version_file).replace('\\', '/')}',"
        else:
            icon_line = "icon=None,"
            version_line = ""

        spec_content = PYINSTALLER_SPEC.format(
            entry_point=str(entry_point).replace('\\', '/'),
            root_dir=str(src_root).replace('\\', '/'),
            app_name=self.cfg.app_name,
            use_upx=str(self.cfg.use_upx),
            console=str(self.cfg.console),
            icon_line=icon_line,
            version_line=version_line,
        )
        spec_file = build_dir / f'{self.cfg.app_name}.spec'
        spec_file.write_text(spec_content, encoding='utf-8')
        return spec_file

    # ── Check dependencies ────────────────────────────────────────────────────

    @staticmethod
    def check_pyinstaller() -> bool:
        try:
            subprocess.check_output([sys.executable, '-m', 'PyInstaller', '--version'],
                                    stderr=subprocess.STDOUT)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    @staticmethod
    def install_pyinstaller(progress_cb=None):
        msg = '[INSTALL] Installing PyInstaller…'
        if progress_cb: progress_cb(msg)
        else: print(msg)
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller',
                                '--quiet', '--no-warn-script-location'])

    @staticmethod
    def check_node() -> bool:
        try:
            subprocess.check_output(['node', '--version'], stderr=subprocess.STDOUT)
            return True
        except FileNotFoundError:
            return False

    # ── Web EXE build ─────────────────────────────────────────────────────────

    def build_web_exe(self, progress_cb=None) -> Path:
        """
        Package Flask server + all assets into a single .exe via PyInstaller.
        Returns path to the output .exe.
        """
        self._progress('[CHECK] Checking PyInstaller…', progress_cb)
        if not self.check_pyinstaller():
            self.install_pyinstaller(progress_cb)

        # Determine source root
        src_root: Path = self.cfg.protected_src or ROOT_DIR

        build_dir = src_root / '_pyinstaller_build'
        build_dir.mkdir(exist_ok=True)

        # Write version info
        self._progress('[GEN] Generating version info…', progress_cb)
        version_file = self._write_version_info(build_dir)

        # Write spec file
        entry_point = src_root / 'app.py'
        spec_file   = self._write_spec(entry_point, build_dir, version_file)

        DIST_DIR.mkdir(exist_ok=True)

        self._progress('[BUILD] Building Web Binary (this may take a few minutes)…', progress_cb)
        result = subprocess.run(
            [
                sys.executable, '-m', 'PyInstaller',
                '--clean',
                '--distpath', str(DIST_DIR),
                '--workpath', str(build_dir / '_work'),
                str(spec_file),
            ],
            capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=str(src_root),
        )

        if result.returncode != 0:
            raise RuntimeError(f'PyInstaller failed:\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}')

        suffix = '.exe' if platform.system() == 'Windows' else ''
        exe_path = DIST_DIR / f'{self.cfg.app_name}{suffix}'
        if not exe_path.exists():
            raise FileNotFoundError(f'Expected output not found: {exe_path}')

        self._progress(f'[OK] Web Binary: {exe_path}', progress_cb)
        return exe_path

    # ── Desktop EXE build ────────────────────────────────────────────────────

    def build_desktop_exe(self, progress_cb=None) -> Path:
        """
        1. Build Web Binary (Flask server)
        2. Copy to electron/resources/server(.exe)
        3. Run npm install in electron/
        4. Run electron-builder to create installer/app
        Returns path to the output.
        """
        if not self.check_node():
            raise EnvironmentError(
                'Node.js not found. Please install Node.js before building the Desktop App.'
            )

        is_windows = (platform.system() == 'Windows')
        binary_name = 'server.exe' if is_windows else 'server'

        # Step 1: Build server binary
        self._progress(f'[STEP 1/4] Build server Binary…', progress_cb)
        # Temporarily enable console=False for production server
        old_console = self.cfg.console
        self.cfg.console = False
        server_binary = self.build_web_exe(progress_cb)
        self.cfg.console = old_console

        # Step 2: Copy server binary into Electron resources
        self._progress(f'[STEP 2/4] Copying {binary_name} to Electron…', progress_cb)
        RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
        dest = RESOURCES_DIR / binary_name

        # Clean up the other platform binary if it exists in the resources folder
        other_binary = 'server' if is_windows else 'server.exe'
        other_path = RESOURCES_DIR / other_binary
        if other_path.exists():
            try:
                other_path.unlink()
            except Exception:
                pass

        shutil.copy2(server_binary, dest)
        self._progress(f'   → {dest}', progress_cb)

        # Step 3: npm install
        self._progress('[STEP 3/4] Installing Node dependencies…', progress_cb)
        result = subprocess.run(
            ['npm', 'install', '--prefer-offline'],
            cwd=str(ELECTRON_DIR), capture_output=True, text=True,
            encoding='utf-8', errors='replace',
            shell=is_windows,
        )
        if result.returncode != 0:
            raise RuntimeError(f'npm install failed:\n{result.stderr[:2000]}')

        # Step 4: electron-builder
        self._progress('[STEP 4/4] Building Electron Desktop App…', progress_cb)
        DIST_ELECTRON.mkdir(exist_ok=True)
        
        builder_flag = '--win' if is_windows else '--mac'
        
        result = subprocess.run(
            ['npx', 'electron-builder', builder_flag],
            cwd=str(ELECTRON_DIR), capture_output=True, text=True,
            encoding='utf-8', errors='replace',
            shell=is_windows,
            env={**os.environ, 'CSC_IDENTITY_AUTO_DISCOVERY': 'false'},
        )
        if result.returncode != 0:
            raise RuntimeError(f'electron-builder failed:\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}')

        # Find output installer
        if is_windows:
            candidates = list(DIST_ELECTRON.glob('*.exe'))
            if not candidates:
                raise FileNotFoundError('electron-builder output .exe not found in dist_electron/')
        else:
            candidates = list(DIST_ELECTRON.glob('*.dmg')) + list(DIST_ELECTRON.glob('*.zip'))
            if not candidates:
                raise FileNotFoundError('electron-builder output .dmg or .zip not found in dist_electron/')

        installer = max(candidates, key=lambda p: p.stat().st_mtime)
        self._progress(f'[OK] Desktop App: {installer}', progress_cb)
        return installer


# ─── CLI entry ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='EveryThingDownloader Packager')
    parser.add_argument('--target', choices=['web', 'desktop', 'both'], default='web')
    parser.add_argument('--version', default='1.0.0')
    parser.add_argument('--name', default='EveryThingDownloader')
    args = parser.parse_args()

    cfg = BuildConfig()
    cfg.version  = args.version
    cfg.app_name = args.name

    p = Packager(cfg)

    if args.target in ('web', 'both'):
        print('\n=== Building Web Binary ===')
        p.build_web_exe()

    if args.target in ('desktop', 'both'):
        print('\n=== Building Desktop App ===')
        p.build_desktop_exe()
