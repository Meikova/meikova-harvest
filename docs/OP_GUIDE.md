# Operating and Usage Guide (Operating Guide) - EveryThingDownloader

This guide provides exhaustive operational, development, packaging, and troubleshooting instructions for the EveryThingDownloader system on **Windows, macOS, and Linux** environments.

---

## 1. Local Workspace & Developer Setup

### 1.1 Python Virtual Environment
1. Open a terminal at the root of the project.
2. Create the virtual environment:
   ```bash
   python -m venv venv
   ```
3. Activate the virtual environment:
   - **Windows (PowerShell)**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     source venv/bin/activate
     ```
4. Install all packages and dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *Note: This installs Flask, flask-cors, yt-dlp, static-ffmpeg, curl-cffi, gallery-dl, quickjs, requests, pyinstaller, pyarmor, and other necessary libraries.*

### 1.2 Electron Development Environment
1. Install Node.js (v20+ recommended) on your machine.
2. Navigate to the `electron/` directory:
   ```bash
   cd electron
   ```
3. Install the Node packages:
   ```bash
   npm install
   ```

### 1.3 Muxer Initialization
When you start the backend for the first time, `static-ffmpeg` automatically pulls down static FFmpeg and FFprobe binaries and registers them in the virtual environment. 
- You can manually test if FFmpeg is configured correctly by running:
  - **Windows**:
    ```powershell
    .\venv\Scripts\python -c "import static_ffmpeg; static_ffmpeg.add_paths(); import subprocess; print(subprocess.check_output(['ffmpeg', '-version']).decode('utf-8'))"
    ```
  - **macOS / Linux**:
    ```bash
    ./venv/bin/python -c "import static_ffmpeg; static_ffmpeg.add_paths(); import subprocess; print(subprocess.check_output(['ffmpeg', '-version']).decode('utf-8'))"
    ```

---

## 2. Launch Procedures

### 2.1 Developer Web Server
To launch only the Flask backend server for web-based access:
- **Windows**:
  ```powershell
  .\venv\Scripts\python.exe app.py
  ```
- **macOS / Linux**:
  ```bash
  source venv/bin/activate
  python app.py
  ```
Open a browser and navigate to `http://localhost:18650`.

### 2.2 Electron Desktop Shell (Developer Mode)
To run the desktop application window mapping to your active Python code:
1. Make sure the Flask server is running in a terminal (step 2.1).
2. Open a separate terminal, navigate to `electron/`, and run:
   ```bash
   npm run dev
   ```

### 2.3 Packaged Desktop Mode (Production)
Once you compile the application using the Build Tool, you can launch the standalone app:
- **Windows**: 
  - Double-click the installer `EveryThingDownloader-Setup-{version}.exe` to install it, or run `EveryThingDownloader-Portable-{version}.exe` directly.
  - The app will open a splash screen saying *"Starting server..."* while starting the hidden backend server (`server.exe`) on a dynamically discovered port starting from 18650, then display the main UI.
- **macOS**: 
  - Install/run the compiled `EveryThingDownloader-{version}.dmg` or unpack the `.zip` archive.
  - The app will spawn the hidden backend server (`server`) dynamically and display the UI.
  - Note: On first launch, macOS Gatekeeper may block the unsigned app. Right-click → "Open" to bypass, or run `xattr -cr /Applications/EveryThingDownloader.app`.
- **Linux**: 
  - Run the `EveryThingDownloader-{version}.AppImage` directly (make it executable first: `chmod +x *.AppImage`), or extract the `.tar.gz` archive.
  - The app will spawn the hidden backend server (`server`) dynamically and display the UI.

### 2.4 Docker Deployment
For headless web server deployment without local environment setup:
```bash
# Start the web server only
docker-compose up app

# Start the Build Tool GUI only
docker-compose up builder

# Start both services
docker-compose up
```
- **Web Server**: Accessible at `http://localhost:18650`
- **Build Tool GUI**: Accessible at `http://localhost:18651`
- Downloads are persisted via volume mount at `./downloads:/app/downloads`.

---

## 3. Advanced Downloader Features & Operations

### 3.1 Session Cookie Management (Bypassing Bot Blocks)
Some platforms (like Twitter/X, Instagram, or age-restricted YouTube videos) require active session cookies to bypass guest-access restrictions.
1. Install a browser extension that exports cookies (e.g. **Get cookies.txt LOCALLY**).
2. Log in to the target platform on your browser.
3. Open the extension, click export, and save the cookies as a text file (Netscape format).
4. In the EveryThingDownloader UI, click **Manage Cookies**.
5. Upload the cookie text file into the designated box for the platform.
6. The backend will automatically apply these cookies to all yt-dlp queries for that platform.

### 3.2 Media Trimming
1. Paste a link and click **ANALYZE LINK**.
2. Click the **Get** button next to your desired video or audio format.
3. In the pop-up modal, adjust the visual range slider handles to define your custom **Start Time** and **End Time**.
4. Click **Download**. The server clips the media on the fly and sends the trimmed file to your browser.

### 3.3 Interactive Webpage Previewing (HTML / Text)
EveryThingDownloader allows you to preview webpage/HTML files directly inside the application interface before downloading.
1. Paste a link (e.g., any website URL that falls back to Webpage Options or provides HTML files) and click **ANALYZE LINK**.
2. Click **Preview** next to the Webpage (HTML / Text) format.
3. The system dynamically proxies the website and renders it inside an interactive, scrollable sandbox container (`<iframe>`), showing you the real live layout.
4. If the format is a plain text file (`.txt`, `.xml`), it displays the raw text content inside the text area for quick inspection or copying.

### 3.4 Bypassing 403 Forbidden & Cloudflare Webpage Blocks
If a webpage is protected by anti-bot challenge screens (like Cloudflare "Just a moment..."):
1. The app automatically utilizes a secure browser-impersonating request engine (`curl_cffi` Chrome impersonator) to query the page.
2. To fully bypass authentication or captcha blocks, ensure you import active session cookies (e.g. using J2TEAM cookie file) via the **Manage Cookies** panel.
3. When you preview or download, the app automatically maps the active session cookies into the proxy server and download tasks, delivering the authentic page content instead of a 403 Forbidden error.

### 3.5 Universal 3-Mode Fullscreen & Auto-Hide Controls
During file preview (Video, Audio, Image, Subtitle transcript, or Webpage/HTML):
1. Click the Fullscreen button on the top modal header or the player control bar to cycle through:
   - **Normal Mode**: Styled modal container overlaying the main dashboard.
   - **Theater / Web Fullscreen**: Expands the preview to occupy the entire browser viewport (perfect for working inside Electron or in a standard browser tab).
   - **Native Fullscreen**: Requests native browser full-screen display.
2. In Theater and Native Fullscreen modes, the player header, custom controls, and mouse cursor automatically fade out and hide after **3 seconds of inactivity** to prevent distraction.
3. Moving the mouse instantly restores visibility to all controls and the cursor.

### 3.6 Subtitles Translation, Deduplication & Shift Alignment
EveryThingDownloader features a highly optimized caption translation engine that runs directly alongside video downloading or previewing.
1. **Interactive Subtitle Translation**:
   - In the video preview screen, select a subtitle option from the subtitles dropdown (e.g. English).
   - To translate, select a target language (default: Vietnamese) and trigger translation.
   - The engine automatically aggregates VTT captions, translates them, and updates the transcript live.
2. **Aggressive Rolling Caption Deduplication**:
   - For platforms like YouTube that output auto-generated subtitles as "rolling" text (words appearing sequentially by clearing previous words), the system automatically analyzes cue pairs.
   - It identifies overlaps by checking containment and word sequences, collapses duplicate rolling chains, and reconstructs clean, complete sentences.
3. **Synchronized Video Trimming**:
   - When downloading a trimmed video segment, the subtitle timestamps are automatically shifted (`new_start = max(0, original_start - trim_start)`). Cues outside the trimmed boundary are discarded.
4. **Visual Layout Optimization**:
   - The engine automatically segments long translated sentences into slides containing a maximum of 10 words. This ensures text blocks never clutter the media player screen or overlap other UI elements.
5. **Hardsub Burn-in & Custom Styling**:
   - When choosing **Hardsub** mode, the subtitles are burned directly into the video frames.
   - The interface features a full font customizer allowing you to choose font family (e.g. Arial to support Vietnamese accents), font size, text color, background box, opacity, outline width, outline color, and alignment/position. These options are synchronized with FFmpeg's subtitles filter.
6. **Softsub Muxing & Auto-load**:
   - When choosing **Softsub** mode, subtitles are muxed into the media file container as a separate stream without re-encoding the video/audio.
   - The subtitle stream is tagged as the default active track, prompting standard media players (like VLC) to display it automatically upon launching the video.

### 3.7 Color Filters & GIF/Shorts Export
1. In the preview modal, open the **Export** tab in the Video Settings menu.
2. **Cinematic Filters**: Select from `Cyberpunk`, `Vintage`, `Noir`, or `Enhance` in the filter dropdown. The filter is applied during download post-processing.
3. **GIF Export**: Select `GIF` from the export type dropdown. The downloaded video segment is converted to a high-quality animated GIF using FFmpeg palettegen (fps=15, max width 480px).
4. **Shorts Export**: Select `Shorts` from the export type dropdown. The video is converted from horizontal to vertical 9:16 format with blurred background padding.

### 3.8 Audio Processing (EQ, Speed, Voice FX)
1. In the Audio Player preview, click the **EQ** button on the control bar to open the side panel.
2. **Equalizer (EQ)**: Adjust 4 frequency bands — Bass (60Hz), Low-Mid (500Hz), High-Mid (2kHz), Treble (10kHz). Use presets: Flat, Bass Boost, Vocal, Acoustic, Electronic, Lo-Fi.
3. **Speed Control**: Navigate to the Speed tab and adjust from 0.25x to 3x. Quick presets: 0.5x, 0.75x, 1x, 1.25x, 1.5x, 2x.
4. **Voice FX**: Navigate to the Voice FX tab and select a preset: Normal, Deep Bass, Bright, Concert Hall, Studio, Lo-Fi, Telephone, Underwater. These effects are applied as FFmpeg audio filters during download.

### 3.9 AI Voiceover (TTS Dubbing)
1. In the Video preview modal, open the **Voiceover** tab in the settings menu.
2. Select a voiceover language and toggle the **AI Overlay** switch to enable.
3. Choose a voice model (e.g., `vi-VN-HoaiMyNeural` for Vietnamese) and adjust rate/pitch sliders.
4. When downloading, the system will: parse subtitle cues → synthesize speech in parallel (15 concurrent edge-tts workers) → sequence clips with 150ms gaps → mix into the video (original audio reduced to 8%, voiceover at 150%).

### 3.10 Telegram Cloud Upload
1. Open the **Settings** dropdown from the header bar.
2. Enter your **Telegram Bot Token** and **Chat ID**.
3. In the preview modal **Export** tab, select `Telegram` as the cloud sync destination.
4. After downloading, the file is automatically uploaded to your Telegram chat via Bot API (supports sendVideo, sendAnimation, sendDocument) and optionally removed from local storage.

### 3.11 Clipboard Auto-Detection (Electron Only)
1. The app monitors the system clipboard every 1.5 seconds for recognized video URLs.
2. Supported platforms: YouTube, TikTok, Facebook, Instagram, Twitter/X, Reddit, Threads, SoundCloud, Pinterest, Vimeo, and direct media file URLs.
3. When a URL is detected, a **Toast notification** appears: *"Phát hiện link video: [URL]"* with a quick **Analyze** button.
4. Toggle this feature on/off via the **Clipboard Auto-Detect** checkbox in the Settings dropdown.

### 3.12 Image Viewer (Zoom, Rotate, Pan)
1. Click **Preview** on any extracted image to open the Image Viewer.
2. **Zoom**: Use `+`/`-` keys, mouse wheel, or the zoom slider (0.5x → 5x).
3. **Rotate**: Press `R` or click the rotate button (90° increments).
4. **Pan**: Click and drag to pan when zoomed in.
5. **Navigate**: Use `←`/`→` arrow keys to move between images in a gallery.
6. **Reset**: Press `0` to reset zoom and rotation to defaults.

### 3.13 Download History Management
1. The **Welcome Dashboard** shows two tabs: **Analyzed History** (localStorage, last 10) and **Downloads History** (SQLite-backed, last 50).
2. Each download entry shows: title, format, file size, timestamp, and action buttons (re-download, delete).
3. Clear all history via the respective **Clear** buttons on each tab.
4. Individual items can be deleted from the server via the delete button on each row.

### 3.14 Settings, UI Customizer & Theme Toggle
1. **Theme Toggle**: Click the sun/moon icon in the header to switch between Dark and Light modes. The transition uses View Transitions API with a circular clip-path animation.
2. **UI Customizer**: Click the palette icon in the header to open the customizer panel:
   - **Accent Themes**: 10+ presets (Default, Emerald, Orchid, Amber, Purple, Rose, Orange, Blue, Peach, Lime) or custom hex colors.
   - **Corner Radius**: Sharp (4px), Rounded (12px), Pill (24px).
   - **Glass Blur**: Adjustable 0–100px backdrop blur intensity.
   - **Typography**: Scale (75%–130%) and font family (Outfit, Jakarta, Inter, Grotesk, System).
   - **Background Effects**: Star Grid, Interactive Ripples, Sound Reactive Grid, Sparkles — each toggleable.
   - **Gravity**: Black Hole (pull), Bulge (push), or None — with adjustable radius and depth.
3. All settings are automatically persisted to `localStorage` and restored on page load.

### 3.15 Keyboard Shortcuts Reference

**Video Player**:
| Key | Action |
|-----|--------|
| `Space` | Play/Pause |
| `M` | Mute/Unmute |
| `←` / `→` | Seek ±10 seconds |
| `↑` / `↓` | Volume up/down |
| `F` | Toggle fullscreen |
| `<` / `>` | Decrease/increase playback speed |
| `[` / `]` | Set trim start/end point |
| `0`–`9` | Jump to 0%–90% of duration |
| `O` | Toggle lights off |
| `H` or `?` | Toggle shortcuts overlay |
| `D` | Export & Download |
| `Esc` | Close preview |

**Audio Player**: Same as Video (Space, M, arrows, `<` `>`, `[` `]`, `0`–`9`, `O`)

**Image Viewer**:
| Key | Action |
|-----|--------|
| `←` / `→` | Previous/Next image |
| `+` / `-` | Zoom in/out |
| `R` | Rotate 90° |
| `0` | Reset zoom & rotation |

**Text/Subtitle Viewer**:
| Key | Action |
|-----|--------|
| `↑` / `↓` | Scroll up/down |
| `PgUp` / `PgDn` | Page scroll |
| `Home` / `End` | Top/bottom |
| `W` | Toggle word wrap |
| `+` / `-` | Font zoom |
| `0` | Reset font & wrap |
| `C` | Copy content |

**Electron Global Shortcuts**: `Ctrl+R`/`F5` Reload, `Ctrl+H` Home, `Ctrl+Shift+D` Downloads folder, `Ctrl+`/`Ctrl-` Zoom, `Ctrl+0` Reset zoom.

---

## 4. Packing the App (Build Tool Operations)

### 4.1 GUI Builder
To access the GUI compiler, launch the dedicated GUI server from your terminal:
```bash
python build_tool/builder_cli.py --gui
```
This launches a separate Flask server on an available port starting from `18651` (to avoid port conflicts with the main backend) and automatically opens your browser.

### 4.2 Interactive CLI Dashboard
To use the terminal-based interactive menu:
```bash
python build_tool/builder_cli.py
```
This renders a color-coded dashboard with numbered menu options for configuring all build parameters.

### 4.3 Metadata Properties
- **Application Name**: Name of the final executable file or application bundle (e.g., `EveryThingDownloader`).
- **Version**: Version string compiled into the file resources (e.g., `1.0.0`). This is also written to `electron/package.json` during the build.
- **Company Name / Copyright / Description**: On Windows, compiled directly into the PE header (which determines how the process is named and grouped inside the **Windows Task Manager**). On macOS, compiled into the application bundle's Info.plist properties.

### 4.4 Code Protection Options
- **AST Scrambling**: Scrambles local variable/function identifiers in python source files.
- **String Encryption**: Encrypts string literals in python source code.
- **Dead Code Injection**: Injects dummy code blocks to confuse analysis (configurable count per file).
- **Anti-Debug**: Terminates execution if a debugger is detected.
- **PyArmor Protection**: Packages files with binary shields to prevent reverse engineering. Supports 3 levels (0=off, 1=standard, 2=advanced) and optional string mixing.

### 4.5 Execution Licensing Restrictions
- **IP Lock**: Restricts execution. Add your authorized public IP address list (retrieved by clicking **Add current IP** in the GUI).
- **Date Expiry**: Select an expiration date. The packaged application will verify the date and exit if it has expired (ensure the date is set to `2027-12-31` or later as the current system year is 2026).
- **Machine ID Lock**: Click **Get Current Machine ID** to fetch your hardware fingerprint. Whitelist this ID to restrict execution to that specific computer.
  - On Windows: fetched using the CSPRODUCT UUID (`wmic csproduct get uuid`).
  - On macOS: a custom SHA256 fingerprint generated from the MAC address, hostname, and CPU processor strings.
  - On Linux: reads `/etc/machine-id` or falls back to DMI product UUID.

### 4.6 Build Output Artifacts

| Platform | Target | Output File |
| :--- | :--- | :--- |
| **Windows** | Web Binary | `dist/EveryThingDownloader-Web-{version}.exe` |
| **Windows** | Desktop Setup | `dist_electron/EveryThingDownloader-Setup-{version}.exe` |
| **Windows** | Desktop Portable | `dist_electron/EveryThingDownloader-Portable-{version}.exe` |
| **Windows** | Desktop MSI | `dist_electron/EveryThingDownloader-{version}.msi` |
| **Windows** | Desktop ZIP | `dist_electron/EveryThingDownloader-{version}-win.zip` |
| **macOS** | Web Binary | `dist/EveryThingDownloader-Web-{version}` |
| **macOS** | Desktop DMG | `dist_electron/EveryThingDownloader-{version}.dmg` |
| **macOS** | Desktop ZIP | `dist_electron/EveryThingDownloader-{version}-mac.zip` |
| **macOS** | Desktop PKG | `dist_electron/EveryThingDownloader-{version}.pkg` |
| **Linux** | Web Binary | `dist/EveryThingDownloader-Web-{version}` |
| **Linux** | Desktop AppImage | `dist_electron/EveryThingDownloader-{version}.AppImage` |
| **Linux** | Desktop Archive | `dist_electron/EveryThingDownloader-{version}.tar.gz` |
| **Linux** | Desktop DEB | `dist_electron/EveryThingDownloader-{version}.deb` |
| **Linux** | Desktop RPM | `dist_electron/EveryThingDownloader-{version}.rpm` |

### 4.7 Publishing & Auto-Update
After building, you can publish releases via:
- **CLI**: `python build_tool/builder_cli.py --publish --publish-tag v1.0.0`
- **CI/CD**: Push a git tag (`git tag v1.0.0 && git push origin v1.0.0`) to trigger the automated GitHub Actions pipeline.

The Electron desktop app includes built-in **Auto-Update** functionality:
1. Periodically checks `update.json` from the public repository.
2. Displays a dialog with version info and changelog.
3. Offers automatic download with progress bar:
   - Evaluates the client platform and pulls the matching package URL from the `platforms` key (`win32` for Windows `.exe`, `darwin_arm64` for macOS ARM `.dmg`, `darwin_x64` for macOS Intel `.dmg`, `linux_x64` for Linux `.AppImage`).
   - Downloads the package into a local temporary folder.
4. Performs native installation:
   - **Windows**: Executes the installer `.exe` in a separate process and quits.
   - **macOS**: Automatically mounts the `.dmg` via `shell.openPath` and quits, enabling easy drag-and-drop replacement.
   - **Linux**: Permissions the `.AppImage` with executable attributes (`chmod +x`) and executes it, or opens the folder for other archive/package formats.

---

## 5. Maintenance & Troubleshooting

| Error / Log Pattern | Root Cause | Resolution Step |
| :--- | :--- | :--- |
| `TLS connect error / OPENSSL_internal` | Conflict between `curl-cffi` OpenSSL DLLs on Windows and other system libraries. | The backend automatically forces `yt-dlp` to bypass `curl-cffi` and fall back to the python native `urllib` legacy handler on Windows platforms. |
| `PyArmor not found` | The `pyarmor` library is missing from the active virtual environment. | **Windows**: Run `.\venv\Scripts\pip install pyinstaller pyarmor`. <br>**macOS/Linux**: Run `./venv/bin/pip install pyinstaller pyarmor`. |
| `â€¦` instead of `…` in build logs | The subprocess logs are decoded in system CP1252 instead of UTF-8. | Resolved. The log streamer now explicitly decodes subprocess stdout using `encoding='utf-8'` and strips ANSI color escape codes before sending lines to the client. |
| Installer build failed: `cannot find specified resource "resources/license.txt"` | The Electron packaging script is missing a license document. | Resolved. We have created a standard license file at `electron/resources/license.txt` to enable NSIS builds. |
| `server.exe` or `server` file not found during Electron packaging | Incorrect relative path inside `electron/package.json` or checking for Windows binary on macOS/Linux. | Resolved. Changed the resource mapping to `resources/server.exe` (Windows) and `resources/server` (macOS/Linux). The packaging scripts are platform-aware. |
| Black CMD windows flashing on desktop during analysis or download | Subprocess commands (like curl or gallery-dl) executed on Windows spawn a console window by default. | Resolved. Injected a global monkey-patch in `app.py` that intercepts all `subprocess.Popen` calls and sets `creationflags=subprocess.CREATE_NO_WINDOW` automatically on Windows. |
| Permission denied when launching server binary inside packaged App | The embedded `server` binary copied into the Electron resources folder doesn't have executable permissions on macOS/Linux. | Resolved. Electron's `main.js` dynamically executes `chmod +x` on the embedded server binary before spawning it on macOS and Linux. |
| macOS Gatekeeper: "EveryThingDownloader" cannot be opened because the developer cannot be verified | Packaged macOS app is unsigned. | Right-click (or Control-click) the application, select "Open", and click "Open" in the dialog, or run `xattr -cr /Applications/EveryThingDownloader.app` in the Terminal. |
| `activate: command not found` on macOS/Linux | Attempting to run Windows activation scripts (`.ps1` or `.bat`) on a Unix shell. | Use `source venv/bin/activate` to activate the python virtual environment. |
| Linux: `SUID sandbox helper binary was found, but is not configured correctly` | Electron AppImage requires `--no-sandbox` flag or proper sysctl configuration on some Linux distributions. | Run the AppImage with `--no-sandbox` flag, or configure the kernel parameter: `sudo sysctl kernel.unprivileged_userns_clone=1`. |
| Docker: `yt-dlp` signature extraction fails | Missing JavaScript engine for yt-dlp's signature decryption. | Resolved. Dockerfile includes Deno installation (`COPY --from=denoland/deno:bin /deno /usr/local/bin/deno`) as the JS runtime for yt-dlp. |
