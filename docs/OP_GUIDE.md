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
| **macOS** | Web Binary | `dist/EveryThingDownloader-Web-{version}` |
| **macOS** | Desktop DMG | `dist_electron/EveryThingDownloader-{version}.dmg` |
| **macOS** | Desktop ZIP | `dist_electron/EveryThingDownloader-{version}.zip` |
| **Linux** | Web Binary | `dist/EveryThingDownloader-Web-{version}` |
| **Linux** | Desktop AppImage | `dist_electron/EveryThingDownloader-{version}.AppImage` |
| **Linux** | Desktop Archive | `dist_electron/EveryThingDownloader-{version}.tar.gz` |

### 4.7 Publishing & Auto-Update
After building, you can publish releases via:
- **CLI**: `python build_tool/builder_cli.py --publish --publish-tag v1.0.0`
- **CI/CD**: Push a git tag (`git tag v1.0.0 && git push origin v1.0.0`) to trigger the automated GitHub Actions pipeline.

The Electron desktop app includes built-in **Auto-Update** functionality:
1. Periodically checks `update.json` from the public repository.
2. Displays a dialog with version info and changelog.
3. Offers automatic download with progress bar, followed by installer launch.

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
