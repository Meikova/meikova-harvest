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


def execute_build(obf_cfg: ObfuscationConfig, build_cfg: BuildConfig, target: str, obfuscate: bool):
    # ── Run obfuscation ───────────────────────────────────────────────────
    protected_src = ROOT_DIR
    if obfuscate:
        output_dir = ROOT_DIR / 'dist' / '_protected'
        info('Starting source code protection…')
        obf = Obfuscator(obf_cfg)
        protected_src = obf.run(ROOT_DIR, output_dir, progress_cb=info)
        ok(f'Source code protected: {protected_src}')
    else:
        warn('Skipping source code protection (use --obfuscate to enable)')

    build_cfg.protected_src = protected_src if obfuscate else None

    # ── Run packaging ─────────────────────────────────────────────────────
    packager = Packager(build_cfg)

    if target in ('web', 'both'):
        info('Building Web Binary…')
        try:
            exe = packager.build_web_exe(progress_cb=info)
            ok(f'Web Binary: {exe}')
        except Exception as e:
            error(f'Build Web Binary failed: {e}')
            sys.exit(1)

    if target in ('desktop', 'both'):
        info('Building Desktop App…')
        try:
            exe = packager.build_desktop_exe(progress_cb=info)
            ok(f'Desktop App: {exe}')
        except Exception as e:
            error(f'Build Desktop App failed: {e}')
            sys.exit(1)

    ok('Completed!')


def run_build(args: argparse.Namespace):
    # Validate platform
    import platform as plt
    host_sys = plt.system().lower()
    if host_sys == 'darwin':
        host_platform = 'macos'
    elif host_sys == 'windows':
        host_platform = 'windows'
    else:
        host_platform = host_sys

    target_platform = getattr(args, 'platform', 'auto')
    if target_platform == 'auto':
        target_platform = host_platform

    if target_platform != host_platform:
        error(
            f"Cross-compilation is not supported by PyInstaller.\n"
            f"  Requested target platform: '{target_platform}'\n"
            f"  Current host platform:     '{host_platform}'\n"
            f"  Please run the build tool on a native {target_platform.upper()} machine to package for {target_platform.upper()}."
        )
        sys.exit(1)

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

    # Auto-add current machine ID if --machine-id without --machine-ids
    if obf_cfg.machine_id_lock and not obf_cfg.allowed_machine_ids:
        mid = get_current_machine_id()
        obf_cfg.allowed_machine_ids = [mid]
        info(f'Auto-detected Machine ID: {mid}')

    execute_build(obf_cfg, build_cfg, args.target, args.obfuscate)


def select_target_menu(current_target: str) -> str:
    while True:
        print("\n" + "-" * 50)
        print(_color("  Select Build Target", "1;35"))
        print("-" * 50)
        print("1. Web Binary (Standalone Backend for browser-based UI)")
        print("2. Desktop App (Backend + Electron Installer/App)")
        print("3. Both Targets (Web Binary and Desktop App)")
        print("0. Back to Main Menu")
        print(f"Current target: {_color(current_target.upper(), '1;32')}")
        
        try:
            choice = input(_color("Choose option [0-3]: ", "1;36")).strip()
        except (KeyboardInterrupt, EOFError):
            return current_target

        if choice == '0' or choice == '':
            return current_target
        elif choice == '1':
            return 'web'
        elif choice == '2':
            return 'desktop'
        elif choice == '3':
            return 'both'
        else:
            print(_color("Invalid choice. Please enter 0-3.", "31"))


def configure_protection_menu(obfuscate: bool, obf_cfg: ObfuscationConfig):
    while True:
        print("\n" + "-" * 50)
        print(_color("  Source Code Protection / Obfuscation Settings", "1;35"))
        print("-" * 50)
        
        status_on_off = "ENABLED" if obfuscate else "DISABLED"
        print(f"1. Enable Source Protection:     [{_color(status_on_off, '1;32' if obfuscate else '1;30')}]")
        print(f"2. PyArmor Obfuscation:          [{_color('YES' if obf_cfg.use_pyarmor else 'NO', '32' if obf_cfg.use_pyarmor else '30')}]")
        print(f"3. PyArmor Level:                [{_color(str(obf_cfg.pyarmor_obf_code), '32')}]")
        print(f"4. PyArmor Scramble Strings:     [{_color('YES' if obf_cfg.pyarmor_mix_str else 'NO', '32' if obf_cfg.pyarmor_mix_str else '30')}]")
        print(f"5. AST Name Scrambling:          [{_color('YES' if obf_cfg.scramble_names else 'NO', '32' if obf_cfg.scramble_names else '30')}]")
        print(f"6. AST String Encoding:          [{_color('YES' if obf_cfg.encode_strings else 'NO', '32' if obf_cfg.encode_strings else '30')}]")
        print(f"7. AST Dead Code Injection:      [{_color('YES' if obf_cfg.inject_dead_code else 'NO', '32' if obf_cfg.inject_dead_code else '30')}]")
        print(f"8. AST Dead Code Count:          [{_color(str(obf_cfg.dead_code_count), '32')}]")
        print(f"9. AST Anti-Debug Checks:        [{_color('YES' if obf_cfg.antidebug else 'NO', '32' if obf_cfg.antidebug else '30')}]")
        print("0. Back to Main Menu")
        
        try:
            choice = input(_color("Choose option [0-9] to edit/toggle: ", "1;36")).strip()
        except (KeyboardInterrupt, EOFError):
            break

        if choice == '0' or choice == '':
            break
        elif choice == '1':
            obfuscate = not obfuscate
        elif choice == '2':
            obf_cfg.use_pyarmor = not obf_cfg.use_pyarmor
        elif choice == '3':
            level = input("Enter PyArmor level [0=off, 1=standard, 2=advanced]: ").strip()
            if level in ('0', '1', '2'):
                obf_cfg.pyarmor_obf_code = int(level)
            else:
                print(_color("Invalid level. Choose 0, 1, or 2.", "31"))
        elif choice == '4':
            obf_cfg.pyarmor_mix_str = not obf_cfg.pyarmor_mix_str
        elif choice == '5':
            obf_cfg.scramble_names = not obf_cfg.scramble_names
        elif choice == '6':
            obf_cfg.encode_strings = not obf_cfg.encode_strings
        elif choice == '7':
            obf_cfg.inject_dead_code = not obf_cfg.inject_dead_code
        elif choice == '8':
            count = input("Enter number of dead code blocks per file: ").strip()
            if count.isdigit():
                obf_cfg.dead_code_count = int(count)
            else:
                print(_color("Must be a number.", "31"))
        elif choice == '9':
            obf_cfg.antidebug = not obf_cfg.antidebug
        else:
            print(_color("Invalid choice.", "31"))
            
    return obfuscate, obf_cfg


def configure_licensing_menu(obf_cfg: ObfuscationConfig) -> ObfuscationConfig:
    import re
    while True:
        print("\n" + "-" * 50)
        print(_color("  Licensing & Expiry Restrictions", "1;35"))
        print("-" * 50)
        
        ip_lock_str = "ENABLED" if obf_cfg.ip_lock else "DISABLED"
        print(f"1. IP Address Lock:         [{_color(ip_lock_str, '1;32' if obf_cfg.ip_lock else '1;30')}]")
        if obf_cfg.ip_lock:
            print(f"   Allowed IPs:             {', '.join(obf_cfg.allowed_ips) if obf_cfg.allowed_ips else '(None set)'}")
            
        expiry_lock_str = "ENABLED" if obf_cfg.date_expiry else "DISABLED"
        print(f"2. Expiry Date Lock:        [{_color(expiry_lock_str, '1;32' if obf_cfg.date_expiry else '1;30')}]")
        if obf_cfg.date_expiry:
            print(f"   Expiry Date:             {obf_cfg.expiry_date or '(None set)'}")
            
        mid_lock_str = "ENABLED" if obf_cfg.machine_id_lock else "DISABLED"
        print(f"3. Machine ID Lock:         [{_color(mid_lock_str, '1;32' if obf_cfg.machine_id_lock else '1;30')}]")
        if obf_cfg.machine_id_lock:
            print(f"   Allowed Machine IDs:     {', '.join(obf_cfg.allowed_machine_ids) if obf_cfg.allowed_machine_ids else '(None set, defaults to current device)'}")
            
        print("0. Back to Main Menu")
        
        try:
            choice = input(_color("Choose option [0-3]: ", "1;36")).strip()
        except (KeyboardInterrupt, EOFError):
            break

        if choice == '0' or choice == '':
            break
        elif choice == '1':
            obf_cfg.ip_lock = not obf_cfg.ip_lock
            if obf_cfg.ip_lock:
                ips = input("Enter allowed IP addresses (space-separated, e.g. '192.168.1.5 127.0.0.1'): ").strip()
                if ips:
                    obf_cfg.allowed_ips = ips.split()
                else:
                    print("No IPs entered. Lock disabled.")
                    obf_cfg.ip_lock = False
        elif choice == '2':
            obf_cfg.date_expiry = not obf_cfg.date_expiry
            if obf_cfg.date_expiry:
                date_str = input("Enter expiry date (YYYY-MM-DD): ").strip()
                if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                    obf_cfg.expiry_date = date_str
                else:
                    print(_color("Invalid format. Must be YYYY-MM-DD. Lock disabled.", "31"))
                    obf_cfg.date_expiry = False
        elif choice == '3':
            obf_cfg.machine_id_lock = not obf_cfg.machine_id_lock
            if obf_cfg.machine_id_lock:
                mids = input("Enter allowed Machine IDs (space-separated, leave empty for current device ID): ").strip()
                if mids:
                    obf_cfg.allowed_machine_ids = mids.split()
                else:
                    current_mid = get_current_machine_id()
                    obf_cfg.allowed_machine_ids = [current_mid]
                    print(f"Using current device Machine ID: {current_mid}")
        else:
            print(_color("Invalid choice.", "31"))
            
    return obf_cfg


def configure_metadata_menu(build_cfg: BuildConfig) -> BuildConfig:
    while True:
        print("\n" + "-" * 50)
        print(_color("  Package & Binary Metadata Settings", "1;35"))
        print("-" * 50)
        print(f"1. App Name:            [{_color(build_cfg.app_name, '32')}]")
        print(f"2. Version:             [{_color(build_cfg.version, '32')}]")
        print(f"3. Icon Path:           [{_color(build_cfg.icon_path or 'Default', '32')}]")
        print(f"4. Show Console Window: [{_color('YES' if build_cfg.console else 'NO', '32' if build_cfg.console else '30')}]")
        print(f"5. Use UPX Compression:  [{_color('YES' if build_cfg.use_upx else 'NO', '32' if build_cfg.use_upx else '30')}]")
        print(f"6. Company/Developer:   [{_color(build_cfg.company or 'None', '32')}]")
        print(f"7. Description:         [{_color(build_cfg.description or 'None', '32')}]")
        print(f"8. Copyright:           [{_color(build_cfg.copyright or 'None', '32')}]")
        print("0. Back to Main Menu")
        
        try:
            choice = input(_color("Choose option [0-8] to edit/toggle: ", "1;36")).strip()
        except (KeyboardInterrupt, EOFError):
            break

        if choice == '0' or choice == '':
            break
        elif choice == '1':
            name = input(f"Enter new App Name [current: {build_cfg.app_name}]: ").strip()
            if name:
                build_cfg.app_name = name
        elif choice == '2':
            version = input(f"Enter new Version [current: {build_cfg.version}]: ").strip()
            if version:
                build_cfg.version = version
        elif choice == '3':
            import platform
            is_win = (platform.system() == 'Windows')
            expected_ext = '.ico' if is_win else '.png or .icns'
            path_str = input(f"Enter path to icon file ({expected_ext}) [current: {build_cfg.icon_path}]: ").strip()
            if path_str:
                path = Path(path_str)
                valid_extensions = ['.ico'] if is_win else ['.png', '.icns', '.ico']
                if path.exists() and path.suffix.lower() in valid_extensions:
                    build_cfg.icon_path = str(path.resolve())
                else:
                    print(_color(f"File does not exist or is not a valid {expected_ext} file.", "31"))
        elif choice == '4':
            build_cfg.console = not build_cfg.console
        elif choice == '5':
            build_cfg.use_upx = not build_cfg.use_upx
        elif choice == '6':
            comp = input(f"Enter Company Name [current: {build_cfg.company}]: ").strip()
            if comp:
                build_cfg.company = comp
        elif choice == '7':
            desc = input(f"Enter File Description [current: {build_cfg.description}]: ").strip()
            if desc:
                build_cfg.description = desc
        elif choice == '8':
            copyr = input(f"Enter Copyright String [current: {build_cfg.copyright}]: ").strip()
            if copyr:
                build_cfg.copyright = copyr
        else:
            print(_color("Invalid choice.", "31"))
            
    return build_cfg


def load_config_menu(obf_cfg: ObfuscationConfig, build_cfg: BuildConfig, target: str, obfuscate: bool):
    try:
        path_str = input("Enter path to configuration JSON file: ").strip()
    except (KeyboardInterrupt, EOFError):
        return obf_cfg, build_cfg, target, obfuscate
        
    if not path_str:
        return obf_cfg, build_cfg, target, obfuscate
    path = Path(path_str)
    if not path.exists():
        print(_color("File not found.", "31"))
        return obf_cfg, build_cfg, target, obfuscate
    try:
        with path.open(encoding='utf-8') as f:
            data = json.load(f)
        obf_cfg = ObfuscationConfig.from_dict(data.get('obfuscation', {}))
        build_cfg = BuildConfig.from_dict(data.get('build', {}))
        target = data.get('target', target)
        obfuscate = data.get('obfuscate', obfuscate)
        print(_color("Configuration loaded successfully!", "32"))
    except Exception as e:
        print(_color(f"Failed to load configuration: {e}", "31"))
    return obf_cfg, build_cfg, target, obfuscate


def save_config_menu(obf_cfg: ObfuscationConfig, build_cfg: BuildConfig, target: str, obfuscate: bool):
    try:
        path_str = input("Enter path to save configuration JSON file [default: build_config.json]: ").strip()
    except (KeyboardInterrupt, EOFError):
        return
        
    if not path_str:
        path_str = "build_config.json"
    path = Path(path_str)
    try:
        data = {
            'target': target,
            'obfuscate': obfuscate,
            'obfuscation': obf_cfg.to_dict(),
            'build': build_cfg.to_dict()
        }
        with path.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(_color(f"Configuration saved to {path.resolve()}", "32"))
    except Exception as e:
        print(_color(f"Failed to save configuration: {e}", "31"))


def run_interactive_menu():
    target = 'both'
    obfuscate = True
    obf_cfg = ObfuscationConfig()
    build_cfg = BuildConfig()

    while True:
        print("\n" + "=" * 65)
        print(_color("  EveryThingDownloader — Advanced Packaging Tool (CLI Menu)", "1;35"))
        print("=" * 65)
        
        # Display current configs
        import platform as plt
        host_sys = plt.system().lower()
        host_platform = 'macOS' if host_sys == 'darwin' else ('Windows' if host_sys == 'windows' else host_sys.capitalize())
        print(f"Target OS Platform:     {_color(host_platform, '1;32')} (Natively Compiled)")
        print(f"[{_color('1', '33')}] Target Output:        {_color(target.upper(), '1;32')}")
        
        obf_status = _color("ENABLED", "1;32") if obfuscate else _color("DISABLED", "1;30")
        print(f"[{_color('2', '33')}] Code Protection:     {obf_status}")
        if obfuscate:
            pyarmor_status = f"Yes (Level {obf_cfg.pyarmor_obf_code})" if obf_cfg.use_pyarmor else "No"
            mix_str_status = "Yes" if obf_cfg.pyarmor_mix_str else "No"
            scramble_status = "Yes" if obf_cfg.scramble_names else "No"
            encode_status = "Yes" if obf_cfg.encode_strings else "No"
            dead_code_status = f"Yes ({obf_cfg.dead_code_count} blocks)" if obf_cfg.inject_dead_code else "No"
            antidebug_status = "Yes" if obf_cfg.antidebug else "No"
            print(f"    - PyArmor: {pyarmor_status} | Mix Strings: {mix_str_status}")
            print(f"    - AST Scramble: {scramble_status} | Encode Strings: {encode_status}")
            print(f"    - Dead Code: {dead_code_status} | Anti-Debug: {antidebug_status}")
            
        ip_status = f"Yes ({', '.join(obf_cfg.allowed_ips)})" if obf_cfg.ip_lock else "No"
        expiry_status = f"Yes ({obf_cfg.expiry_date})" if obf_cfg.date_expiry else "No"
        mid_status = f"Yes ({len(obf_cfg.allowed_machine_ids)} device(s))" if obf_cfg.machine_id_lock else "No"
        print(f"[{_color('3', '33')}] Licensing & Expiry:   IP Lock: {ip_status} | Expiry: {expiry_status} | Machine ID: {mid_status}")
        
        print(f"[{_color('4', '33')}] Package Metadata:")
        print(f"    - App Name:    {build_cfg.app_name} (Version: {build_cfg.version})")
        print(f"    - Company:     {build_cfg.company}")
        print(f"    - Description: {build_cfg.description}")
        print(f"    - Copyright:   {build_cfg.copyright}")
        icon_display = Path(build_cfg.icon_path).name if build_cfg.icon_path else 'Default'
        print(f"    - Icon:        {icon_display}")
        console_status = "Yes" if build_cfg.console else "No"
        upx_status = "Yes" if build_cfg.use_upx else "No"
        print(f"    - Show Console: {console_status} | Use UPX: {upx_status}")
        
        mid = get_current_machine_id()
        mid_display = mid[:8] + "..." + mid[-8:] if len(mid) > 16 else mid
        print(f"[{_color('5', '33')}] Hardware Fingerprint: Current Machine ID: {_color(mid_display, '36')}")
        print("-" * 65)
        print(f"[{_color('B', '1;32')}] Start Build    [{_color('L', '36')}] Load Config    [{_color('S', '36')}] Save Config    [{_color('Q', '1;31')}] Quit")
        print("-" * 65)
        
        try:
            choice = input(_color("Enter option: ", "1;36")).strip().upper()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting CLI.")
            break
            
        if choice == 'Q':
            print("Goodbye.")
            break
        elif choice == '1':
            target = select_target_menu(target)
        elif choice == '2':
            obfuscate, obf_cfg = configure_protection_menu(obfuscate, obf_cfg)
        elif choice == '3':
            obf_cfg = configure_licensing_menu(obf_cfg)
        elif choice == '4':
            build_cfg = configure_metadata_menu(build_cfg)
        elif choice == '5':
            print(f"\nYour complete Machine ID:\n  {_color(mid, '1;36')}")
            try:
                input("\nPress Enter to return to main menu...")
            except (KeyboardInterrupt, EOFError):
                pass
        elif choice == 'L':
            obf_cfg, build_cfg, target, obfuscate = load_config_menu(obf_cfg, build_cfg, target, obfuscate)
        elif choice == 'S':
            save_config_menu(obf_cfg, build_cfg, target, obfuscate)
        elif choice == 'B':
            print("\n" + "=" * 65)
            info("Starting build process from CLI menu...")
            print("=" * 65)
            # Auto-add current machine ID if machine-id is locked without specific machine-ids
            if obf_cfg.machine_id_lock and not obf_cfg.allowed_machine_ids:
                obf_cfg.allowed_machine_ids = [mid]
                info(f'Auto-detected Machine ID: {mid}')
            try:
                execute_build(obf_cfg, build_cfg, target, obfuscate)
            except Exception as e:
                error(f"Build failed: {e}")
            try:
                input("\nPress Enter to return to main menu...")
            except (KeyboardInterrupt, EOFError):
                pass
        else:
            print(_color("Invalid choice. Please choose again.", "31"))


def main():
    if len(sys.argv) == 1:
        run_interactive_menu()
        return

    parser = argparse.ArgumentParser(
        prog='builder_cli',
        description='EveryThingDownloader — Advanced Packaging Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Simple web binary build
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
    parser.add_argument('--platform', choices=['windows', 'macos', 'auto'],
                        default='auto', help='Target platform to build for')

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
    build.add_argument('--icon', help='Path to icon file (.ico on Windows, .png/.icns on macOS)')
    build.add_argument('--upx', action='store_true',
                       help='Use UPX compression (reduces size, slower startup)')
    build.add_argument('--console', action='store_true',
                       help='Show console window on launch')
    build.add_argument('--company', help='Company/Developer name metadata')
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
        import webbrowser
        gui_path = Path(__file__).parent / 'builder_gui.html'
        webbrowser.open(f'file:///{gui_path.as_posix()}')
        return

    run_build(args)


if __name__ == '__main__':
    main()
