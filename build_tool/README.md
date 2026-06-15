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
# Open interface in browser
python build_tool/builder_cli.py --gui

# Or open directly
start build_tool/builder_gui.html
```

---

## CLI Usage

### Build Web Server EXE (Simple)
```bash
python build_tool/builder_cli.py --target web
```

### Build Desktop App EXE
```bash
python build_tool/builder_cli.py --target desktop
```

### Build Both
```bash
python build_tool/builder_cli.py --target both
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
python build_tool/builder_cli.py --target web --obfuscate --expire 2025-12-31
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
| Date Expiry | `--expire YYYY-MM-DD` | Terminate execution after a specified date |
| Machine ID Lock | `--machine-id` | Lock build to a specific hardware fingerprint |

---

## Web EXE Build Flow

```
Source code
    | (if --obfuscate)
    v
Obfuscator (AST transform + PyArmor)
    |
    v
PyInstaller → dist/EveryThingDownloader.exe
```

## Desktop EXE Build Flow

```
Source code
    | (if --obfuscate)
    v
Obfuscator
    |
    v
PyInstaller → server.exe
    | copy to electron/resources/
    v
electron-builder → dist_electron/EveryThingDownloader-Setup.exe
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
└── resources/           — Icon + bundled server.exe
```
