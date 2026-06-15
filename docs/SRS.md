# Software Requirements Specification (SRS) - EveryThingDownloader

## 1. Technical Stack & Component Boundaries

The system components are bound by the following version requirements and runtime frameworks:

| Component | Technology | Minimum Version | Deployment Scope |
| :--- | :--- | :--- | :--- |
| **Backend Runtime** | Python interpreter | `3.12.x` | Dev, packaged server, standalone web |
| **Web Server** | Flask framework | `3.0.3` | WSGI local server instance |
| **Desktop Shell** | Electron, Node.js | Electron `31.7.7` | Client desktop window container |
| **Media Downloader** | `yt-dlp` | Active Master | Subprocess core download engine |
| **Image Downloader** | `gallery-dl` | Active Master | Subprocess photo/gallery scraper |
| **Muxer / Trimmer** | FFmpeg binaries | Static `7.x` | Binary wrapper via `static-ffmpeg` |
| **Compiler** | PyInstaller | `6.x` | Compiler GUI backend execution |
| **Obfuscator Shield** | PyArmor | `8.x` (Free tier) | AST/Binary packer shielding |

---

## 2. System Architecture & Inter-Process Communication

In Desktop mode, Electron functions as a Chromium-based UI frame while spawning and managing the Python server process lifecycle:

1. **Process Spawn**: Electron's `main.js` executes `resources/server.exe` as a headless background process using Node's `child_process.spawn`.
2. **Health Probe**: The main process polls `/api/machine-id` until it receives a valid JSON response (maximum 15 retries), verifying the server is up before rendering the main `BrowserWindow`.
3. **Shutdown Event**: When the Electron window is closed, the main process fires a termination signal (`SIGTERM` / `taskkill`) to the PID of `server.exe` to guarantee no orphaned server processes are left in memory.

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

---

### 4.2 Security & Obfuscation Build Pipeline

When a build is triggered via `/api/build/start`, the obfuscation module executes the following steps:

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
     - On Windows, extracts CSPRODUCT UUID: `wmic csproduct get uuid`
     - Terminates if it does not match the whitelisted Machine IDs.
