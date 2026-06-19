# Software Requirements Specification (SRS) - EveryThingDownloader

## 1. Technical Stack & Component Boundaries

The system components are bound by the following version requirements and runtime frameworks:

| Component | Technology | Minimum Version | Deployment Scope |
| :--- | :--- | :--- | :--- |
| **Backend Runtime** | Python interpreter | `3.12.x` | Dev, packaged server, standalone web |
| **Web Server** | Flask framework | `3.0.3` | WSGI local server instance |
| **Desktop Shell** | Electron, Node.js | Electron `31.x` | Client desktop window container |
| **Media Downloader** | `yt-dlp` | `>=2026.3.17` | Subprocess core download engine |
| **Image Downloader** | `gallery-dl` | Active Master | Subprocess photo/gallery scraper |
| **Muxer / Trimmer** | FFmpeg binaries | Static `7.x` | Binary wrapper via `static-ffmpeg` |
| **JS Runtime** | QuickJS | Active | JavaScript engine for yt-dlp signature handling |
| **HTTP Engine** | `curl-cffi` | Latest | Chrome-impersonating HTTP client for anti-bot bypass |
| **Compiler** | PyInstaller | `6.x` | Compiler for server binary packaging |
| **Obfuscator Shield** | PyArmor | `8.x` (Free tier) | AST/Binary packer shielding |
| **Supported Platforms** | Windows, macOS, Linux | — | All build targets and CI/CD runners |

---

## 2. System Architecture & Inter-Process Communication

In Desktop mode, Electron functions as a Chromium-based UI frame while spawning and managing the Python server process lifecycle:

1. **Process Spawn**: Electron's `main.js` executes the backend server binary as a headless background process using Node's `child_process.spawn`.
   - On Windows: spawns `resources/server.exe`
   - On macOS: spawns `resources/server` (with `chmod +x` applied dynamically)
   - On Linux: spawns `resources/server` (with `chmod +x` applied dynamically)
2. **Port Discovery**: The main process finds a free TCP port starting from `18650` using `net.createServer()` and passes the discovered port to the backend via the `FLASK_PORT` environment variable.
3. **Health Probe**: The main process polls `http://127.0.0.1:<port>/` at 500ms intervals until it receives a valid response with status code < 500 (maximum 60-second timeout), verifying the server is up before rendering the main `BrowserWindow`.
4. **Shutdown Event**: When the Electron window is closed, the main process fires a termination signal:
   - On Windows: `taskkill /pid <PID> /f /t` to kill the entire process tree.
   - On macOS/Linux: `SIGTERM` to the server process PID.
5. **Minimize to Tray**: Closing the window hides it to system tray instead of quitting. The app can be restored via double-clicking the tray icon.

---

## 3. Core Processing Mechanics

### 3.1 Media Downloading & Format Muxing
The server uses `yt-dlp` to extract streams. When high-resolution video (1080p, 2K, 4K) is requested, yt-dlp downloads the video and audio streams as separate files into `downloads/temp_<uuid>/` and invokes the embedded FFmpeg binary to mux them:
```bash
yt-dlp --format "{format_id}" --merge-output-format mp4 --ffmpeg-location "{ffmpeg_bin_path}" -o "downloads/temp_<uuid>/media.%(ext)s" "{url}"
```

### 3.2 Media Trimming Pipeline
Trimming is executed as a post-processing or direct transcoding pipeline using FFmpeg.
1. **Direct Copy (No Muxing required)**:
   ```bash
   ffmpeg -y -ss {start_time} -to {end_time} -i {input_path} -c:v copy -c:a copy {output_path}
   ```
2. **Re-encoding Fallback (Required for precise cuts at non-keyframes)**:
   ```bash
   ffmpeg -y -ss {start_time} -to {end_time} -i {input_path} -c:v libx264 -preset superfast -crf 23 -c:a aac -b:a 192k {output_path}
   ```

---

## 4. API Specifications (OpenAPI Style)

### 4.1 Downloader APIs

#### POST `/api/info`
- **Request Body**:
  ```json
  {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "custom_ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."
  }
  ```
- **Responses**:
  - `200 OK`: Returns format details, subtitles, images, and description.
    ```json
    {
      "status": "success",
      "title": "Rick Astley - Never Gonna Give You Up",
      "uploader": "Rick Astley",
      "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
      "duration": 212,
      "formats": [
        {
          "format_id": "137+140",
          "resolution": "1080p",
          "ext": "mp4",
          "filesize": 45120300,
          "type": "video"
        }
      ],
      "images": [],
      "subtitles": [
        {"lang": "en", "name": "English"}
      ],
      "description": "The official video for..."
    }
    ```

#### POST `/api/download`
- **Request Body**:
  ```json
  {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format_id": "137+140",
    "ext": "mp4",
    "trim_start": "00:00:10",
    "trim_end": "00:01:00"
  }
  ```
- **Response**: Streams the output file back to the browser via chunked stream response:
  - **Headers**:
    - `Content-Type`: `application/octet-stream`
    - `Content-Disposition`: `attachment; filename="Never Gonna Give You Up [dQw4w9WgXcQ].mp4"`

#### GET `/api/system/proxy-sub`
- **Query Parameters**:
  - `url` (required): Target URL of the subtitle file or HTML page.
  - `mode` (optional): Output format handler (`vtt`, `html`, or `txt`, defaults to `vtt`).
  - `client_id` (optional): Associated client session to load cookies.
- **Processing Logic**:
  - Bypasses CORS restrictions on the client side.
  - If a `client_id` is supplied, reads and injects Netscape session cookies from `downloads/cookies/cookies_{client_id}.txt`.
  - Uses `curl_cffi` requests engine (impersonating Chrome browser) to fetch target content to circumvent anti-bot filters (Cloudflare, IP blocks).
  - If `mode=vtt`, decodes and validates VTT subtitles layout, responding with `Content-Type: text/vtt; charset=utf-8`.
  - If `mode=html`, responds with the raw HTML payload using `Content-Type: text/html; charset=utf-8`.
  - Otherwise, responds with plain text under `text/plain; charset=utf-8`.

#### POST `/api/system/translate-sub`
- **Request Body**:
  ```json
  {
    "url": "https://www.youtube.com/api/timedtext?...",
    "content": "WEBVTT\n...",
    "target_lang": "vi"
  }
  ```
- **Responses**:
  - `200 OK`: Returns the translated, formatted, and deduplicated VTT content:
    ```json
    {
      "status": "success",
      "translated_vtt": "WEBVTT\nKind: captions\nLanguage: vi\n\n00:00:10.000 --> 00:00:15.000\nNội dung phụ đề..."
    }
    ```
- **Processing Logic**:
  - Accepts either a subtitle URL (`url` parameter) or raw subtitle content (`content` parameter).
  - Resolves local subtitle streams if `url` starts with `/api/download/file/`.
  - Converts input formats (XML, TimedText) into WebVTT via `ensure_vtt_content`.
  - Writes to a temporary `.vtt` file and invokes `translate_vtt_file` from `utils.ffmpeg`.
  - Returns the translated VTT content and cleans up the temporary files.

---

### 4.2 Subtitle Processing & Normalization Pipeline
The subtitle subsystem (`utils/ffmpeg.py` -> `translate_vtt_file`) performs structural operations on WebVTT cues before translation:
1. **Conversion & Normalization**:
   - `ensure_vtt_content(text)` detects `<transcript>` or `<timedtext>` XML elements.
   - Extracts timestamps and text, returning formatted standard `WEBVTT` text.
2. **Micro-duration Filtering**:
   - Cues with a duration $\le 50$ms (often empty transition frames generated by YouTube) are discarded.
3. **Rolling Caption Deduplication**:
   - Detects rolling continuations where cue B adds text to the tail of cue A.
   - Compares consecutive cues using tail-head word sequence overlap (checking sequence match of $\ge 2$ words) and substring containment.
   - Groups overlapping cues into "chains", taking the start time of the first cue, the end time of the last, and merging the non-overlapping word sequences.
4. **Batch Translation Engine**:
   - Packages cues into batch blocks of maximum 4000 characters using index tokens (e.g. `[idx] text\n[idx2] text2`).
   - Dispatches a single API request to `translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={lang}`.
   - Reconstructs and maps the translated strings back to their original indexes. Falls back to individual requests on parse failures.
5. **Timeline Shift Alignment**:
   - Adjusts timestamps according to video cropping parameters: `new_start = max(0, start - trim_start)`.
6. **Sentence Visual Segmenting**:
   - Splits long translated caption cues into smaller sub-cues containing at most 10 words, calculating appropriate linear segment durations to keep captions highly readable.

---

### 4.3 Webpage Fallback Downloads
For target pages that do not expose direct video/audio URLs (generic web pages), the system returns a `"generic_fallback"` option.
1. **Detection**: Checked in `tasks/download.py` when `format_id == "generic_fallback"`.
2. **Download Handling**:
   - The thread bypasses the subprocess `yt-dlp` pipeline.
   - Searches and parses client-associated Netscape cookie files.
   - Executes standard/secure request fetch via `fetch_html` from `extractors/generic.py`.
   - Saves the webpage markup to a local `.html` file under `downloads/temp_{download_id}/`.
   - The `/api/download/file/<download_id>` endpoint serves the completed HTML file using the appropriate `text/html; charset=utf-8` MIME type.

### 4.4 Webpage Preview Component
The webpage preview renders inside the main preview modal:
- **HTML Container**: `#preview-webpage-container` displays a full-size `<iframe>` (`#preview-webpage-iframe`).
- **Source Mapping**: Points to `/api/system/proxy-sub?mode=html&url={url}&client_id={clientId}`.
- **Sizing**: Constrained by flexbox styles, automatically expanding to full-viewport size in Web Fullscreen and Native Fullscreen modes.

---

### 4.5 Security & Obfuscation Build Pipeline

When a build is triggered via `/api/build/start` (Web GUI) or CLI commands, the obfuscation module executes the following steps:

1. **AST Scrambling**:
   The code parses Python sources into Abstract Syntax Trees using Python's `ast` module. It renames local variables, functions, and class definitions to randomized hashes (e.g. `_0x8f2a1b`) while preserving standard keywords, built-ins, and external API symbols.
2. **String Encryption**:
   Plaintext string literals in the AST are extracted and encoded (XOR with a dynamic key or base64 masked). They are replaced with runtime decoder nodes:
   ```python
   # Original: url = "https://youtube.com"
   # Obfuscated: url = _decrypt_str("aHR0cHM6Ly95b3V0dWJlLmNvbQ==", key=42)
   ```
3. **PyArmor Compilation**:
   Runs PyArmor to generate binary-packed obfuscated code shields:
   ```bash
   pyarmor gen --output dist/_protected/_work_obfuscated --obf-code 1 --mix-str app.py
   ```
4. **License Guard Injection**:
   Injects checks into the entry point file:
   - **IP Lock**: Queries `api.ipify.org` on startup and terminates if the public IP is not in the compiled whitelist.
   - **Expiry Limit**: Compares local system time (and optionally queries an NTP server to prevent local clock tampering) against the compiled expiration date.
   - **Machine ID Lock**: Checks the local system fingerprint:
     - On Windows: extracts CSPRODUCT UUID via `wmic csproduct get uuid`.
     - On macOS: computes a custom SHA256 hardware fingerprint based on the MAC address, hostname, and CPU processor strings.
     - On Linux: reads `/etc/machine-id` or falls back to DMI product UUID via `dmidecode`.
     - Terminates if it does not match the whitelisted Machine IDs.

5. **Compilation Interfaces**:
   - **API / Web Interface**: Initiated via `/api/build/start` HTTP POST request.
   - **Web Builder GUI**: Launched via `python build_tool/builder_cli.py --gui`. It spawns a local Flask server running on a dynamically allocated port (starting from `18651` upwards) to avoid conflicts with the main application server, and triggers a browser window opening `http://127.0.0.1:<port>/`.
   - **Interactive CLI Menu Dashboard**: Run via `python build_tool/builder_cli.py` without arguments. Displays a color-coded terminal dashboard where developers can toggle target output systems (Web, Desktop, or Both), configure obfuscation settings (PyArmor, AST scrambling, etc.), set up licensing rules (IP lock, expiration dates like `2027-12-31`, Machine ID whitelist), customize packaging metadata, view the current system Machine ID, load/save configuration profiles, and trigger packaging interactively.
   - **Non-Interactive CLI**: Run via `python build_tool/builder_cli.py --target <web|desktop|both> [options]`. Suitable for scripting and CI/CD integration.

### 4.6 Multi-Platform CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/build-and-release.yml`) automates multi-platform builds:

1. **Matrix Strategy**: Runs builds in parallel on `windows-latest`, `macos-latest`, and `ubuntu-latest`.
2. **Build Steps per Runner**:
   - Python 3.12 + Node.js 20 setup with dependency caching
   - Version extraction from git tag
   - Full build (`--target both --obfuscate`) producing Web Binary + Desktop App
   - Web Binary renaming with platform suffix (e.g., `-Windows.exe`, `-macOS`, `-Linux`)
3. **Release Job**:
   - Downloads all build artifacts from all 3 platform runners
   - Calculates SHA-256 checksums for each file
   - Generates detailed release notes with changelog, asset descriptions, and checksum table
   - Publishes release to both private and public repositories
   - Updates `update.json` in the public repository with multi-platform URLs (`win32`, `darwin`, `linux` keys under `platforms`) for auto-update integration

### 4.7 Docker Deployment

The project provides Docker support for running the web server and build tool in containers:

- **Dockerfile**: Based on `python:3.10-slim`, installs FFmpeg, Deno (for yt-dlp), and all Python dependencies.
- **docker-compose.yml**: Defines two services:
  - `app`: Runs the Flask web server on port `18650` with downloads volume mount.
  - `builder`: Runs the Build Tool GUI on port `18651` with full project volume mount.
