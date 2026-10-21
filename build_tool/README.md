# Meikova Harvest — Build Tool & Packaging Guide

## Overview

The Build Tool provides three usage modes:
- **GUI** (`builder_gui.html`) — Visual web interface served via a dedicated Flask server
- **CLI** (`builder_cli.py`) — Non-interactive command-line interface with full argument support
- **Interactive Menu** (`builder_cli.py` without arguments) — Color-coded terminal dashboard

**Supported Platforms**: Windows, macOS, Linux

> **Note**: PyInstaller does not support cross-compilation. You must run the build tool on the target platform's native host (e.g., build on macOS to produce macOS binaries). GitHub Actions CI/CD handles multi-platform builds automatically.

---

## Installation Requirements

```bash
# Python dependencies
pip install -r requirements.txt
# (includes pyinstaller, pyarmor, and all other required packages)

# Node.js (for Desktop build) — download from https://nodejs.org
# Then install Electron dependencies:
cd electron
npm install
```

---

## GUI Usage

```bash
# Open the GUI Builder web interface
# This launches a dedicated local Flask server on a dynamic port (starting from 18651) and opens it in your default browser
python build_tool/builder_cli.py --gui
```

---

## CLI Usage

### Build Web Server Binary (Simple)
```bash
# Auto-detects host platform. Output:
# Windows → dist/Meikova Harvest-Web-1.0.0.exe
# macOS   → dist/Meikova Harvest-Web-1.0.0
# Linux   → dist/Meikova Harvest-Web-1.0.0
python build_tool/builder_cli.py --target web
```

### Build Desktop App
```bash
# Windows → dist_electron/Meikova Harvest-Setup-1.0.0.exe (NSIS), Meikova Harvest-Portable-1.0.0.exe, Meikova Harvest-1.0.0.msi, Meikova Harvest-1.0.0-win.zip
# macOS   → dist_electron/Meikova Harvest-1.0.0.dmg, Meikova Harvest-1.0.0-mac.zip, Meikova Harvest-1.0.0.pkg
# Linux   → dist_electron/Meikova Harvest-1.0.0.AppImage, Meikova Harvest-1.0.0.tar.gz, Meikova Harvest-1.0.0.deb, Meikova Harvest-1.0.0.rpm
python build_tool/builder_cli.py --target desktop
```

### Build Both
```bash
python build_tool/builder_cli.py --target both
```

### Target Platform Selection
```bash
# By default, it auto-detects the host system. You can explicitly verify:
python build_tool/builder_cli.py --target web --platform windows
python build_tool/builder_cli.py --target web --platform macos
python build_tool/builder_cli.py --target web --platform linux

# Note: PyInstaller does not support cross-compilation. 
# You must run the build tool on a native host to package for that platform.
# GitHub Actions CI/CD automates this by running builds on all 3 platform runners.
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
# View this machine's ID (works on all platforms)
python build_tool/builder_cli.py --machine-id-info

# Build locked to current machine
python build_tool/builder_cli.py --target web --obfuscate --machine-id

# Build locked to a list of specific Machine IDs
python build_tool/builder_cli.py --target web --obfuscate \
    --machine-ids abc123... def456...
```

### Publishing to GitHub
```bash
# Automatically update update.json, create git tag and push to GitHub
python build_tool/builder_cli.py --target both --obfuscate --publish --publish-tag v1.0.0
```

### All Options
```bash
python build_tool/builder_cli.py --help
```

---

## Interactive CLI Menu Dashboard

```bash
# Launch without arguments to open the interactive menu
python build_tool/builder_cli.py
```

The dashboard displays:
- **Target OS Platform**: Auto-detected (Windows, macOS, or Linux)
- **[1] Target Output**: Toggle between Web, Desktop, or Both
- **[2] Code Protection**: Configure PyArmor, AST Scrambling, String Encoding, Dead Code Injection, Anti-Debug
- **[3] Licensing & Expiry**: IP Lock, Expiry Date, Machine ID Lock
- **[4] Package Metadata**: App Name, Version, Icon, Company, Description, Copyright, Console, UPX
- **[5] Hardware Fingerprint**: View current machine's Machine ID
- **[B] Start Build**: Execute the build pipeline
- **[L] Load Config**: Load settings from a JSON file
- **[S] Save Config**: Save current settings to a JSON file
- **[Q] Quit**

---

## Protection Features

| Feature | CLI Argument | Description |
|-----------|-------------|-------|
| PyArmor | `--pyarmor` | Encrypt Python bytecode (free tier) |
| Obfuscation level | `--pyarmor-level 0/1/2` | PyArmor complexity level |
| Mix Strings | `--pyarmor-mix-str` | Scramble string literals with PyArmor |
| Name scrambling | `--scramble` | Scramble variable/function names randomly |
| String encryption | `--encode-strings` | Encode string literals using Base64 |
| Dead code | `--dead-code` | Inject dummy code blocks for analysis noise |
| Dead code count | `--dead-code-count N` | Number of dead code blocks per file (default: 15) |
| Anti-debug | `--antidebug` | Terminate execution if a debugger is detected |
| IP Lock | `--ip-lock IP1 IP2` | Restrict execution to authorized IP addresses |
| Expiry Date | `--expire YYYY-MM-DD` | Terminate execution after a specified date |
| Machine ID Lock | `--machine-id` | Lock build to a specific hardware fingerprint |
| Target Platform | `--platform windows/macos/linux/auto` | Target platform to build for (requires native host) |

---

## Web Binary Build Flow

```
Source code
    | (if --obfuscate)
    v
Obfuscator (AST transform + PyArmor)
    |
    v
PyInstaller → dist/Meikova Harvest-Web-{version}.exe (Windows)
              dist/Meikova Harvest-Web-{version} (macOS)
              dist/Meikova Harvest-Web-{version} (Linux)
```

## Desktop App Build Flow

```
Source code
    | (if --obfuscate)
    v
Obfuscator
    |
    v
PyInstaller → server.exe (Windows) / server (macOS/Linux)
    | copy to electron/resources/
    v
electron-builder → dist_electron/Meikova Harvest-Setup-{version}.exe   (Windows NSIS)
                   dist_electron/Meikova Harvest-Portable-{version}.exe (Windows Portable)
                   dist_electron/Meikova Harvest-{version}.dmg          (macOS DMG)
                   dist_electron/Meikova Harvest-{version}.zip          (macOS ZIP)
                   dist_electron/Meikova Harvest-{version}.AppImage     (Linux AppImage)
                   dist_electron/Meikova Harvest-{version}.tar.gz       (Linux Archive)
```

---

## Running Electron in Development Mode

```bash
cd electron
npm run dev
# or
npm start
```

---

## Directory Structure

```
build_tool/
├── __init__.py          — Package exports
├── obfuscator.py        — Code protection (AST transforms, PyArmor, license guards)
├── packager.py          — PyInstaller + electron-builder wrapper (multi-platform)
├── builder_cli.py       — CLI interface + Interactive Menu + GUI server
├── builder_gui.html     — GUI web interface (single-file HTML app)
├── electron_builder.js  — Electron build script
├── git_helper.py        — Git release publishing helper
└── build_config.json    — Default configuration template

electron/
├── main.js              — Electron main process (server lifecycle, tray, auto-update)
├── preload.js           — IPC bridge (contextBridge API)
├── splash.html          — Splash screen (loading animation)
├── package.json         — npm config + electron-builder config (win/mac/linux targets)
└── resources/           — Icon files + bundled server binary
    ├── icon.ico         — Windows icon
    ├── icon.png         — macOS/Linux icon
    ├── license.txt      — License file for NSIS installer
    └── server.exe/server — Bundled server binary (platform-dependent)
```
