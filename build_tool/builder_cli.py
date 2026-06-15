"""
builder_cli.py — Command-line interface for EveryThingDownloader Build Tool

Usage:
  python builder_cli.py --target web
  python builder_cli.py --target desktop --obfuscate --ip-lock 1.2.3.4 5.6.7.8
  python builder_cli.py --target both --expire 2025-12-31 --machine-id
  python builder_cli.py --machine-id-info
  python builder_cli.py --gui
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Fix Windows terminal encoding for Unicode text
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Make sure parent dir is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build_tool.obfuscator import ObfuscationConfig, Obfuscator, get_current_machine_id
from build_tool.packager import BuildConfig, Packager

ROOT_DIR = Path(__file__).resolve().parent.parent


def _color(text: str, code: str) -> str:
    """ANSI color wrapper (works in Windows Terminal / PowerShell)."""
    return f'\033[{code}m{text}\033[0m'


def info(msg):  print(_color(f'[INFO ] {msg}', '36'))
def ok(msg):    print(_color(f'[OK   ] {msg}', '32'))
def warn(msg):  print(_color(f'[WARN ] {msg}', '33'))
def error(msg): print(_color(f'[ERROR] {msg}', '31'))


def run_build(args: argparse.Namespace):
    # ── Obfuscation config ────────────────────────────────────────────────
    obf_cfg = ObfuscationConfig()
    obf_cfg.use_pyarmor      = args.pyarmor
    obf_cfg.pyarmor_obf_code = args.pyarmor_level
    obf_cfg.pyarmor_mix_str  = args.pyarmor_mix_str
    obf_cfg.scramble_names   = args.scramble
    obf_cfg.encode_strings   = args.encode_strings
    obf_cfg.inject_dead_code = args.dead_code
    obf_cfg.dead_code_count  = args.dead_code_count
    obf_cfg.antidebug        = args.antidebug

    obf_cfg.ip_lock       = bool(args.ip_lock)
    obf_cfg.allowed_ips   = list(args.ip_lock) if args.ip_lock else []

    obf_cfg.date_expiry   = bool(args.expire)
    obf_cfg.expiry_date   = args.expire or ''

    obf_cfg.machine_id_lock       = args.machine_id
    obf_cfg.allowed_machine_ids   = list(args.machine_ids) if args.machine_ids else []

    # ── Build config ──────────────────────────────────────────────────────
    build_cfg = BuildConfig()
    build_cfg.app_name    = args.name
    build_cfg.version     = args.version
    build_cfg.use_upx     = args.upx
    build_cfg.console     = args.console
    if args.icon:
        build_cfg.icon_path = args.icon
    if args.company:
        build_cfg.company = args.company
    if args.description:
        build_cfg.description = args.description
    if args.copyright:
        build_cfg.copyright = args.copyright

    # ── Load from JSON config file if provided ────────────────────────────
    if args.config:
        cfg_path = Path(args.config)
        with cfg_path.open(encoding='utf-8') as f:
            data = json.load(f)
        obf_cfg = ObfuscationConfig.from_dict(data.get('obfuscation', {}))
        build_cfg = BuildConfig.from_dict(data.get('build', {}))

    # ── Run obfuscation ───────────────────────────────────────────────────
    protected_src = ROOT_DIR
    if args.obfuscate:
        output_dir = ROOT_DIR / 'dist' / '_protected'
        info('Starting source code protection…')
        obf = Obfuscator(obf_cfg)
        protected_src = obf.run(ROOT_DIR, output_dir, progress_cb=info)
        ok(f'Source code protected: {protected_src}')
    else:
        warn('Skipping source code protection (use --obfuscate to enable)')

    build_cfg.protected_src = protected_src if args.obfuscate else None

    # ── Run packaging ─────────────────────────────────────────────────────
    packager = Packager(build_cfg)

    if args.target in ('web', 'both'):
        info('Building Web EXE…')
        try:
            exe = packager.build_web_exe(progress_cb=info)
            ok(f'Web EXE: {exe}')
        except Exception as e:
            error(f'Build Web EXE failed: {e}')
            sys.exit(1)

    if args.target in ('desktop', 'both'):
        info('Building Desktop EXE…')
        try:
            exe = packager.build_desktop_exe(progress_cb=info)
            ok(f'Desktop EXE: {exe}')
        except Exception as e:
            error(f'Build Desktop EXE failed: {e}')
            sys.exit(1)

    ok('Completed!')


def main():
    parser = argparse.ArgumentParser(
        prog='builder_cli',
        description='EveryThingDownloader — Advanced Packaging Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Simple web exe build
  python builder_cli.py --target web

  # Build with full protection
  python builder_cli.py --target both --obfuscate --ip-lock 1.2.3.4 --expire 2025-12-31

  # Display this machine's Machine ID
  python builder_cli.py --machine-id-info

  # Open the GUI interface
  python builder_cli.py --gui
        '''
    )

    parser.add_argument('--target', choices=['web', 'desktop', 'both'],
                        default='web', help='Output type to build')

    # Obfuscation options
    obf = parser.add_argument_group('Source Code Protection')
    obf.add_argument('--obfuscate', action='store_true',
                     help='Enable all source code protection features')
    obf.add_argument('--no-obfuscate', dest='obfuscate', action='store_false')
    obf.add_argument('--pyarmor', action='store_true', default=True,
                     help='Use PyArmor (free tier)')
    obf.add_argument('--no-pyarmor', dest='pyarmor', action='store_false')
    obf.add_argument('--pyarmor-level', type=int, choices=[0, 1, 2], default=1,
                     help='PyArmor obfuscation level (0=off, 1=standard, 2=advanced)')
    obf.add_argument('--pyarmor-mix-str', action='store_true', default=True,
                     help='Scramble string literals with PyArmor')
    obf.add_argument('--scramble', action='store_true', default=True,
                     help='Scramble variable/function names (AST)')
    obf.add_argument('--encode-strings', action='store_true', default=True,
                     help='Encode string literals')
    obf.add_argument('--dead-code', action='store_true', default=True,
                     help='Inject dead code to confuse analysis')
    obf.add_argument('--dead-code-count', type=int, default=15,
                     help='Number of dead code blocks per file')
    obf.add_argument('--antidebug', action='store_true', default=True,
                     help='Add anti-debug checks')

    # License restrictions
    lic = parser.add_argument_group('Usage Restrictions')
    lic.add_argument('--ip-lock', nargs='+', metavar='IP',
                     help='Only allow execution on these IP addresses')
    lic.add_argument('--expire', metavar='YYYY-MM-DD',
                     help='Expiry date (the application will refuse to run after this date)')
    lic.add_argument('--machine-id', action='store_true',
                     help='Lock by Machine ID (hardware fingerprint)')
    lic.add_argument('--machine-ids', nargs='+', metavar='ID',
                     help='List of allowed Machine IDs (default: current machine)')

    # Build options
    build = parser.add_argument_group('Build Settings')
    build.add_argument('--name', default='EveryThingDownloader',
                       help='Output application name')
    build.add_argument('--version', default='1.0.0', help='Application version')
    build.add_argument('--icon', help='Path to icon file (.ico)')
    build.add_argument('--upx', action='store_true',
                       help='Use UPX compression (reduces size, slower startup)')
    build.add_argument('--console', action='store_true',
                       help='Show console window on launch')
    build.add_argument('--company', help='Company name metadata')
    build.add_argument('--description', help='File description metadata')
    build.add_argument('--copyright', help='Copyright string metadata')

    # Misc
    parser.add_argument('--config', metavar='FILE',
                        help='Load configuration from a JSON file')
    parser.add_argument('--machine-id-info', action='store_true',
                        help='Display this machine\'s Machine ID and exit')
    parser.add_argument('--gui', action='store_true',
                        help='Open the GUI interface in the browser')

    args = parser.parse_args()

    # Handle special modes
    if args.machine_id_info:
        mid = get_current_machine_id()
        print(f'\nThis machine\'s Machine ID:\n\n  {mid}\n')
        print('Copy this ID to use with --machine-ids when building.')
        return

    if args.gui:
        import webbrowser, os
        gui_path = Path(__file__).parent / 'builder_gui.html'
        webbrowser.open(f'file:///{gui_path.as_posix()}')
        return

    # Auto-add current machine ID if --machine-id without --machine-ids
    if args.machine_id and not args.machine_ids:
        mid = get_current_machine_id()
        args.machine_ids = [mid]
        info(f'Auto-detected Machine ID: {mid}')

    run_build(args)


if __name__ == '__main__':
    main()
