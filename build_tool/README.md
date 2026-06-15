# EveryThingDownloader — Build Tool & Packaging Guide

## Overview

The Build Tool provides two usage modes:
- **GUI** (`builder_gui.html`) — Visual web interface
- **CLI** (`builder_cli.py`) — Command-line interface

---

## Installation Requirements

```bash
# Python dependencies
pip install pyinstaller pyarmor

# Node.js (for Desktop build) — download from https://nodejs.org
# Then install Electron dependencies:
cd electron
npm install
```

---

## GUI Usage

```bash
# Open the GUI Builder web interface
# This launches a dedicated local Flask server on a dynamic port (starting from 5001) and opens it in your default browser
python build_tool/builder_cli.py --gui
```

---

## CLI Usage

### Build Web Server Binary (Simple)
```bash
# Windows (outputs dist/EveryThingDownloader.exe)
# macOS (outputs dist/EveryThingDownloader)
python build_tool/builder_cli.py --target web
```

### Build Desktop App
```bash
# Packages the server and Electron app.
# Windows (outputs dist_electron/EveryThingDownloader Setup 1.0.0.exe or portable)
# macOS (outputs dist_electron/EveryThingDownloader-1.0.0.dmg or .zip)
python build_tool/builder_cli.py --target desktop
```

### Build Both
```bash
python build_tool/builder_cli.py --target both
```

### Target Platform Selection
```bash
# By default, it auto-detects the host system. You can explicitly specify the target:
python build_tool/builder_cli.py --target web --platform macos
python build_tool/builder_cli.py --target web --platform windows

# Note: PyInstaller does not support cross-compilation. You must run the build tool on a native macOS machine to build for macOS, or Windows for Windows.
```

### Build with Code Protection
```bash
python build_tool/builder_cli.py --target web --obfuscate
```

### Build with IP Lock
```bash
python build_tool/builder_cli.py --target web --obfuscate --ip-lock 1.2.3.4 5.6.7.8
```

### Build with Date Expiry
```bash
# Packs a date expiry check. Since the current year is 2026, set it to 2027-12-31 or later
python build_tool/builder_cli.py --target web --obfuscate --expire 2027-12-31
```

### Build with Machine ID Lock
```bash
# View this machine's ID
python build_tool/builder_cli.py --machine-id-info

# Build locked to current machine
python build_tool/builder_cli.py --target web --obfuscate --machine-id

# Build locked to a list of specific Machine IDs
python build_tool/builder_cli.py --target web --obfuscate \
    --machine-ids abc123... def456...
```

### All Options
```bash
python build_tool/builder_cli.py --help
```

---

## Protection Features

| Feature | CLI Argument | Description |
|-----------|-------------|-------|
| PyArmor | `--pyarmor` | Encrypt Python bytecode (free tier) |
| Obfuscation level | `--pyarmor-level 0/1/2` | PyArmor complexity level |
| Name scrambling | `--scramble` | Scramble variable/function names randomly |
| String encryption | `--encode-strings` | Encode string literals using Base64 |
| Dead code | `--dead-code` | Inject dummy code blocks for analysis noise |
| Anti-debug | `--antidebug` | Terminate execution if a debugger is detected |
| IP Lock | `--ip-lock IP1 IP2` | Restrict execution to authorized IP addresses |
| Expiry Date | `--expire YYYY-MM-DD` | Terminate execution after a specified date |
| Machine ID Lock | `--machine-id` | Lock build to a specific hardware fingerprint |
| Target Platform | `--platform windows/macos/auto` | Target platform to build for (requires native host) |

---

## Web Binary Build Flow

```
Source code
    | (if --obfuscate)
    v
Obfuscator (AST transform + PyArmor)
    |
    v
PyInstaller → dist/EveryThingDownloader.exe (Windows)
              dist/EveryThingDownloader (macOS)
```

## Desktop App Build Flow

```
Source code
    | (if --obfuscate)
    v
Obfuscator
    |
    v
PyInstaller → server.exe (Windows) / server (macOS)
    | copy to electron/resources/
    v
electron-builder → dist_electron/EveryThingDownloader Setup 1.0.0.exe (Windows NSIS)
                   dist_electron/EveryThingDownloader-1.0.0.dmg (macOS DMG)
```

---

## Running Electron in Development Mode

```bash
cd electron
npm start
# or
npm run dev
```

---

## Directory Structure

```
build_tool/
├── __init__.py          — Package exports
├── obfuscator.py        — Code protection (fully self-implemented)
├── packager.py          — PyInstaller + electron-builder wrapper
├── builder_cli.py       — CLI interface
├── builder_gui.html     — GUI web interface
├── electron_builder.js  — Electron build script
└── build_config.json    — Default configuration template

electron/
├── main.js              — Electron main process
├── preload.js           — IPC bridge
├── splash.html          — Splash screen
├── package.json         — npm config + electron-builder config
└── resources/           — Icon + bundled server.exe (Windows) or server (macOS)
```
