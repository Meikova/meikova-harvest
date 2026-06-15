# Operating and Usage Guide (Operating Guide) - EveryThingDownloader

This guide provides exhaustive operational, development, packaging, and troubleshooting instructions for the EveryThingDownloader system on a Windows 10/11 environment.

---

## 1. Local Workspace & Developer Setup

### 1.1 Python Virtual Environment
1. Open a PowerShell terminal at the root of the project (`D:\JOB\DEV\EveryThingDownloader`).
2. Create the virtual environment:
   ```powershell
   python -m venv venv
   ```
3. Activate the virtual environment:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
4. Install all packages and dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
   *Note: This installs Flask, flask-cors, yt-dlp, static-ffmpeg, requests, and other necessary libraries.*

### 1.2 Electron Development Environment
1. Install Node.js (v20+ recommended) on your machine.
2. Navigate to the `electron/` directory:
   ```powershell
   cd electron
   ```
3. Install the Node packages:
   ```powershell
   npm install
   ```

### 1.3 Muxer Initialization
When you start the backend for the first time, `static-ffmpeg` automatically pulls down static FFmpeg and FFprobe binaries and registers them in the virtual environment. 
- You can manually test if FFmpeg is configured correctly by running:
  ```powershell
  .\venv\Scripts\python -c "import static_ffmpeg; static_ffmpeg.add_paths(); import subprocess; print(subprocess.check_output(['ffmpeg', '-version']).decode('utf-8'))"
  ```

---

## 2. Launch Procedures

### 2.1 Developer Web Server
To launch only the Flask backend server for web-based access:
```powershell
.\venv\Scripts\python.exe app.py
```
Open a browser and navigate to `http://localhost:5000`.

### 2.2 Electron Desktop Shell (Developer Mode)
To run the desktop application window mapping to your active Python code:
1. Make sure the Flask server is running in a terminal (step 2.1).
2. Open a separate terminal, navigate to `electron/`, and run:
   ```powershell
   npm run dev
   ```

### 2.3 Packaged Desktop Mode (Production)
Once you compile the application using the GUI Builder, you can launch the standalone app:
1. Double-click the installer `EveryThingDownloader Setup 1.0.0.exe` to install it, or run `EveryThingDownloader-Portable-1.0.0.exe`.
2. The app will open a splash screen saying *"Starting server..."* while starting the hidden backend server (`server.exe`) on port 5000, then display the main UI.

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

---

## 4. Packing the App (GUI Builder Operations)

Navigate to `http://localhost:5000/builder` in your browser to access the GUI compiler.

### 4.1 Metadata Properties
- **Application Name**: Name of the final executable file (e.g., `EveryThingDownloader`).
- **Version**: Version string compiled into the file resources (e.g., `1.0.0`).
- **Company Name / Copyright / Description**: Compiled directly into the PE header. These properties determine how the application's process is named and grouped inside the **Windows Task Manager**.

### 4.2 Code Protection Options
- **AST Scrambling**: Scrambles local variable/function identifiers in python source files.
- **String Encryption**: Encrypts string literals in python source code.
- **PyArmor Protection**: Packages files with binary shields to prevent reverse engineering.

### 4.3 Execution Licensing Restrictions
- **IP Lock**: Restricts execution. Add your authorized public IP address list (retrieved by clicking **Add current IP**).
- **Date Expiry**: Select an expiration date. The packaged application will verify the date and exit if it has expired.
- **Machine ID Lock**: Click **Get Current Machine ID** to fetch your hardware fingerprint. Whitelist this ID to restrict execution to that specific computer.

### 4.4 Interactive CLI Builder Menu
Instead of utilizing the browser-based Web GUI, developers can run the build tool directly within their preferred terminal.
1. Open a PowerShell or Command Prompt terminal.
2. Launch the script without any command line arguments:
   ```powershell
   python build_tool/builder_cli.py
   ```
3. A color-coded terminal dashboard will render displaying current settings:
   - **Target Output**: Toggle compiled targets between Web, Desktop, or Both.
   - **Code Protection**: Configure PyArmor levels, AST identifier scrambling, string encryption, dead code injection (custom block counts), and anti-debug guards.
   - **Licensing & Expiry**: Configure IP white-listing, set system expiry date constraints, and check/add hardware Machine ID locks.
   - **Package Metadata**: Customize exe headers (App Name, Version, Company Name, Copyright, File Description, custom Icon path, and UPX compression).
   - **Config Profile Management**: Save/load settings directly from configuration JSON files.
4. Press `B` to trigger the build pipeline using the selected parameters.


---

## 5. Maintenance & Troubleshooting

| Error / Log Pattern | Root Cause | Resolution Step |
| :--- | :--- | :--- |
| `TLS connect error / OPENSSL_internal` | Conflict between `curl-cffi` OpenSSL DLLs on Windows and other system libraries. | The backend automatically forces `yt-dlp` to bypass `curl-cffi` and fall back to the python native `urllib` legacy handler on Windows platforms. |
| `PyArmor not found` | The `pyarmor` library is missing from the active virtual environment. | Run: `.\venv\Scripts\pip install pyinstaller pyarmor` to restore the packaging libraries. |
| `â€¦` instead of `…` in build logs | The subprocess logs are decoded in system CP1252 instead of UTF-8. | Resolved. The log streamer now explicitly decodes subprocess stdout using `encoding='utf-8'` and strips ANSI color escape codes before sending lines to the client. |
| Installer build failed: `cannot find specified resource "resources/license.txt"` | The Electron packaging script is missing a license document. | Resolved. We have created a standard license file at `electron/resources/license.txt` to enable NSIS builds. |
| `server.exe` file not found during Electron packaging | Incorrect relative path inside `electron/package.json`. | Resolved. Changed the resource mapping from `../resources/server.exe` to `resources/server.exe`. |
| Black CMD windows flashing on desktop during analysis or download | Subprocess commands (like curl or gallery-dl) executed on Windows spawn a console window by default. | Resolved. Injected a global monkey-patch in `app.py` that intercepts all `subprocess.Popen` calls and sets `creationflags=subprocess.CREATE_NO_WINDOW` automatically on Windows. |
