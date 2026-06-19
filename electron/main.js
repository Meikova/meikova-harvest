/**
 * Electron Main Process — EveryThingDownloader
 *
 * Responsibilities:
 *  1. Find a free TCP port
 *  2. Spawn the Flask Python server (or bundled server.exe)
 *  3. Poll until Flask is ready, then show the BrowserWindow
 *  4. Manage system tray icon
 *  5. Kill the Flask process cleanly on exit
 */

const {
  app,
  BrowserWindow,
  Menu,
  Tray,
  ipcMain,
  shell,
  dialog,
  nativeImage,
  globalShortcut,
} = require('electron');

const path  = require('path');
const http  = require('http');
const net   = require('net');
const fs    = require('fs');
const { spawn, execSync } = require('child_process');

// ─── Configuration ────────────────────────────────────────────────────────────
const APP_NAME    = 'EveryThingDownloader';
const DEFAULT_PORT = 18650;
const SPLASH_WAIT  = 600;   // ms before showing splash
const SERVER_TIMEOUT = 60000; // ms to wait for Flask (60 s)
const isDev = process.argv.includes('--dev') || !app.isPackaged;

// ─── Global state ─────────────────────────────────────────────────────────────
let mainWindow   = null;
let splashWindow = null;
let tray         = null;
let flaskProcess = null;
let serverPort   = DEFAULT_PORT;
let serverReady  = false;

// ─── Logging ──────────────────────────────────────────────────────────────────
const log = {
  info:  (...a) => console.log( '[INFO ]', ...a),
  warn:  (...a) => console.warn( '[WARN ]', ...a),
  error: (...a) => console.error('[ERROR]', ...a),
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Find a free TCP port starting from `start`. */
function findFreePort(start = DEFAULT_PORT) {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(start, '127.0.0.1', () => {
      const { port } = server.address();
      server.close(() => resolve(port));
    });
    server.on('error', () => findFreePort(start + 1).then(resolve).catch(reject));
  });
}

/** Poll GET http://127.0.0.1:<port>/ until 200 or timeout. */
function waitForServer(port, timeoutMs = SERVER_TIMEOUT) {
  return new Promise((resolve, reject) => {
    const start    = Date.now();
    const interval = setInterval(() => {
      if (Date.now() - start > timeoutMs) {
        clearInterval(interval);
        return reject(new Error(`Server did not start within ${timeoutMs / 1000}s`));
      }
      const req = http.get(`http://127.0.0.1:${port}/`, (res) => {
        if (res.statusCode < 500) {
          clearInterval(interval);
          resolve();
        }
      });
      req.on('error', () => {}); // ignore ECONNREFUSED while server is starting
      req.setTimeout(1000, () => req.destroy());
    }, 500);
  });
}

/** Resolve the path to the Flask server entry-point. */
function resolveServerPath() {
  if (app.isPackaged) {
    const isWindows = process.platform === 'win32';
    const binaryName = isWindows ? 'server.exe' : 'server';
    return path.join(process.resourcesPath, binaryName);
  }
  // In development, run app.py with the active Python / venv
  return null; // signals "use Python"
}

/** Resolve the Python executable path (dev mode). */
function resolvePythonPath() {
  const isWindows = process.platform === 'win32';
  const venvPy = isWindows
    ? path.join(__dirname, '..', 'venv', 'Scripts', 'python.exe')
    : path.join(__dirname, '..', 'venv', 'bin', 'python');
  try {
    require('fs').accessSync(venvPy);
    return venvPy;
  } catch {
    return isWindows ? 'python' : 'python3'; // fall back to system Python
  }
}

// ─── Flask server launch ──────────────────────────────────────────────────────

async function startFlaskServer() {
  serverPort = await findFreePort(DEFAULT_PORT);
  log.info(`Starting Flask on port ${serverPort}`);

  const env = {
    ...process.env,
    FLASK_PORT: String(serverPort),
    FLASK_ENV:  isDev ? 'development' : 'production',
    PYTHONUNBUFFERED: '1',
  };

  const serverExe = resolveServerPath();

  if (serverExe) {
    // Read build config if it exists
    let showConsole = false;
    try {
      const cfgPath = path.join(__dirname, 'config.json');
      if (fs.existsSync(cfgPath)) {
        const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
        showConsole = !!cfg.console;
      }
    } catch (e) {
      log.error('Failed to read config.json:', e);
    }

    const isWindows = process.platform === 'win32';

    // Production: run bundled server.exe
    if (showConsole && isWindows) {
      // Run in a new console window on Windows using 'start /wait'
      flaskProcess = spawn('cmd.exe', [
        '/c',
        'start',
        'EveryThingDownloader Backend Server',
        '/wait',
        serverExe,
        '--port',
        String(serverPort)
      ], {
        env,
        windowsHide: false,
      });
    } else {
      // Run silently in background
      flaskProcess = spawn(serverExe, ['--port', String(serverPort)], {
        env,
        windowsHide: true,
      });
    }
  } else {
    // Development: run app.py via Python
    const pythonExe = resolvePythonPath();
    const appPy     = path.join(__dirname, '..', 'app.py');
    flaskProcess    = spawn(pythonExe, [appPy, '--port', String(serverPort)], {
      env,
      cwd: path.join(__dirname, '..'),
      windowsHide: true,
    });
  }

  flaskProcess.stdout?.on('data', (d) => log.info('[Flask]', d.toString().trimEnd()));
  flaskProcess.stderr?.on('data', (d) => log.warn('[Flask]', d.toString().trimEnd()));
  flaskProcess.on('error', (err) => log.error('Flask process error:', err));
  flaskProcess.on('exit', (code) => {
    log.info(`Flask exited with code ${code}`);
    flaskProcess = null;
    if (mainWindow && !app.isQuitting) {
      dialog.showErrorBox(APP_NAME, 'The internal server stopped unexpectedly.\nPlease restart the application.');
    }
  });
}

function killFlaskServer() {
  if (flaskProcess) {
    log.info('Killing Flask server…');
    try {
      // On Windows, taskkill kills the whole process tree
      if (process.platform === 'win32') {
        execSync(`taskkill /pid ${flaskProcess.pid} /f /t`);
      } else {
        flaskProcess.kill('SIGTERM');
      }
    } catch (e) {
      log.warn('Failed to kill Flask process:', e.message);
    }
    flaskProcess = null;
  }
}

// ─── Window creation ──────────────────────────────────────────────────────────

function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width:  480,
    height: 320,
    frame:  false,
    transparent: true,
    resizable: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    webPreferences: {
      preload:         path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: getAppIcon(),
  });

  splashWindow.loadFile(path.join(__dirname, 'splash.html'));
  splashWindow.center();
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width:  1366,
    height: 900,
    minWidth:  1024,
    minHeight: 720,
    show: false,
    frame: false,            // Frameless — custom SVG controls injected via JS
    titleBarStyle: 'hidden',
    backgroundColor: '#0a0a0f',
    webPreferences: {
      preload:          path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration:  false,
    },
    icon:  getAppIcon(),
    title: APP_NAME,
  });

  mainWindow.loadURL(`http://127.0.0.1:${serverPort}/`);

  mainWindow.webContents.on('did-finish-load', () => {
    // ── Inject drag-region CSS ──
    mainWindow.webContents.insertCSS(`
      /* ── Global: no text selection except inputs ── */
      *, *::before, *::after {
        -webkit-user-select: none;
        user-select: none;
      }
      input, textarea, [contenteditable="true"] {
        -webkit-user-select: text;
        user-select: text;
      }

      /* ── Dedicated drag strip at top of window ── */
      #electron-drag-strip {
        position: fixed;
        top: 0;
        left: 0;
        right: 138px;      /* leave 138px on right for the 3 win-control buttons */
        height: 30px;
        z-index: 99998;
        -webkit-app-region: drag;
        cursor: grab;
      }
      #electron-drag-strip:active {
        cursor: grabbing;
      }

      /* ── Window control buttons ── */
      #electron-wincontrols {
        position: fixed;
        top: 0;
        right: 0;
        z-index: 99999;
        display: flex;
        align-items: center;
        height: 30px;
        padding: 0;
        -webkit-app-region: no-drag;
      }
      #electron-wincontrols .wc-btn {
        width: 46px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        background: transparent;
        border: none;
        outline: none;
        opacity: 0.45;
        transition: opacity 0.15s, background 0.15s;
      }
      #electron-wincontrols .wc-btn:hover {
        opacity: 1;
        background: rgba(255, 255, 255, 0.08);
      }
      #electron-wincontrols .wc-btn.close-btn:hover {
        background: rgba(232, 17, 35, 0.85);
        opacity: 1;
      }
      #electron-wincontrols .wc-btn svg {
        width: 10px;
        height: 10px;
        stroke: #b0b0c0;
        fill: none;
        stroke-width: 1.4;
        stroke-linecap: round;
        stroke-linejoin: round;
        pointer-events: none;
      }
      #electron-wincontrols .wc-btn.close-btn:hover svg {
        stroke: #fff;
      }
    `).catch(() => {});

    // ── Inject custom SVG window control buttons ──
    mainWindow.webContents.executeJavaScript(`
      (function() {
        if (document.getElementById('electron-wincontrols')) return;

        const bar = document.createElement('div');
        bar.id = 'electron-wincontrols';

        // Minimize — horizontal line
        bar.innerHTML += \`
          <button class="wc-btn min-btn" title="Minimize" onclick="window.electronAPI?.minimizeWindow()">
            <svg viewBox="0 0 11 11">
              <line x1="1" y1="5.5" x2="10" y2="5.5"/>
            </svg>
          </button>
        \`;

        // Maximize / Restore — square
        bar.innerHTML += \`
          <button class="wc-btn max-btn" title="Maximize" onclick="window.electronAPI?.maximizeWindow()">
            <svg viewBox="0 0 11 11">
              <rect x="1.5" y="1.5" width="8" height="8" rx="0.8"/>
            </svg>
          </button>
        \`;

        // Close — × cross
        bar.innerHTML += \`
          <button class="wc-btn close-btn" title="Close" onclick="window.electronAPI?.closeWindow()">
            <svg viewBox="0 0 11 11">
              <line x1="1.5" y1="1.5" x2="9.5" y2="9.5"/>
              <line x1="9.5" y1="1.5" x2="1.5" y2="9.5"/>
            </svg>
          </button>
        \`;

        document.body.appendChild(bar);

        // ── Drag strip (transparent bar at top for dragging the window) ──
        if (!document.getElementById('electron-drag-strip')) {
          const strip = document.createElement('div');
          strip.id = 'electron-drag-strip';
          document.body.appendChild(strip);
        }
      })();
    `).catch(() => {});

    if (!serverReady) return;
    showMainWindow();
  });

  // Intercept navigation — keep all links inside the app
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('close', (e) => {
    if (!app.isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => { mainWindow = null; });

  // Open DevTools in dev mode
  if (isDev) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }
}

function showMainWindow() {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.destroy();
    splashWindow = null;
  }
  if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
  }
}

function getAppIcon() {
  const fs = require('fs');

  // Candidate paths, preferred order: .ico for Windows, .png as fallback
  const isWin = process.platform === 'win32';
  const ext   = isWin ? ['icon.ico', 'icon.png'] : ['icon.png', 'icon.ico'];

  const searchDirs = app.isPackaged
    ? [
        path.join(process.resourcesPath, '..', 'resources'),
        path.join(process.resourcesPath),
      ]
    : [
        path.join(__dirname, 'resources'),
        path.join(__dirname, '..', 'static'),
      ];

  for (const dir of searchDirs) {
    for (const filename of ext) {
      const full = path.join(dir, filename);
      if (fs.existsSync(full)) {
        const img = nativeImage.createFromPath(full);
        if (!img.isEmpty()) return img;
      }
    }
  }

  // Final fallback: use app logo.png from static/
  const fallback = path.join(__dirname, '..', 'static', 'logo.png');
  if (fs.existsSync(fallback)) {
    const img = nativeImage.createFromPath(fallback);
    if (!img.isEmpty()) return img;
  }

  return nativeImage.createEmpty();
}

const https = require('https');

function downloadFile(url, destPath, onProgress, onComplete, onError) {
  const request = https.get(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
  }, (response) => {
    // Handle HTTP Redirects (e.g. GitHub release downloads redirecting to AWS S3)
    if (response.statusCode >= 300 && response.statusCode < 400 && response.headers.location) {
      log.info('Redirecting to: ' + response.headers.location);
      return downloadFile(response.headers.location, destPath, onProgress, onComplete, onError);
    }

    if (response.statusCode !== 200) {
      onError(new Error('Failed to download: Status Code ' + response.statusCode));
      return;
    }

    const totalBytes = parseInt(response.headers['content-length'], 10) || 0;
    let downloadedBytes = 0;
    const fileStream = fs.createWriteStream(destPath);

    response.on('data', (chunk) => {
      downloadedBytes += chunk.length;
      fileStream.write(chunk);
      if (totalBytes > 0) {
        const percent = Math.round((downloadedBytes / totalBytes) * 100);
        const transferred = (downloadedBytes / (1024 * 1024)).toFixed(1);
        const totalMB = (totalBytes / (1024 * 1024)).toFixed(1);
        onProgress({ percent, transferred, total: totalMB });
      }
    });

    response.on('end', () => {
      fileStream.end();
      onComplete();
    });

    response.on('error', (err) => {
      fileStream.end();
      fs.unlink(destPath, () => {});
      onError(err);
    });
  });

  request.on('error', (err) => {
    fs.unlink(destPath, () => {});
    onError(err);
  });
}

function startAutoUpdate(url, version) {
  log.info('Starting auto update. Downloading from ' + url);
  
  const progressWindow = new BrowserWindow({
    width: 420,
    height: 160,
    parent: mainWindow || undefined,
    modal: true,
    resizable: false,
    minimizable: false,
    maximizable: false,
    title: 'Downloading Update...',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });
  progressWindow.setMenu(null);
  
  const htmlContent = 
    '<!DOCTYPE html>' +
    '<html>' +
    '<head>' +
    '  <meta charset="UTF-8">' +
    '  <style>' +
    '    body {' +
    '      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;' +
    '      margin: 20px;' +
    '      background-color: #0f0f15;' +
    '      color: #ffffff;' +
    '      overflow: hidden;' +
    '    }' +
    '    h3 { margin-top: 0; font-size: 15px; font-weight: 500; color: #ff527b; }' +
    '    .progress-bar-container {' +
    '      width: 100%;' +
    '      background-color: #252530;' +
    '      border-radius: 6px;' +
    '      overflow: hidden;' +
    '      margin-top: 12px;' +
    '    }' +
    '    .progress-bar {' +
    '      width: 0%;' +
    '      height: 12px;' +
    '      background: linear-gradient(90deg, #ff527b, #ff7e5f);' +
    '      border-radius: 6px;' +
    '      transition: width 0.1s ease-in-out;' +
    '    }' +
    '    .status-text {' +
    '      margin-top: 8px;' +
    '      font-size: 12px;' +
    '      color: #a0a0b0;' +
    '      display: flex;' +
    '      justify-content: space-between;' +
    '    }' +
    '  </style>' +
    '</head>' +
    '<body>' +
    '  <h3>Downloading EveryThingDownloader Setup v' + version + '...</h3>' +
    '  <div class="progress-bar-container">' +
    '    <div id="bar" class="progress-bar"></div>' +
    '  </div>' +
    '  <div class="status-text">' +
    '    <span id="pct">Connecting...</span>' +
    '    <span id="stats">0.0 / 0.0 MB</span>' +
    '  </div>' +
    '  <script>' +
    '    const { ipcRenderer } = require("electron");' +
    '    ipcRenderer.on("progress", (event, data) => {' +
    '      document.getElementById("bar").style.width = data.percent + "%";' +
    '      document.getElementById("pct").innerText = data.percent + "%";' +
    '      document.getElementById("stats").innerText = data.transferred + " / " + data.total + " MB";' +
    '    });' +
    '  </script>' +
    '</body>' +
    '</html>';
  
  progressWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(htmlContent));
  
  const destName = 'EveryThingDownloader-Setup-' + version + '.exe';
  const destPath = path.join(app.getPath('temp'), destName);
  
  downloadFile(url, destPath, 
    (prog) => {
      if (!progressWindow.isDestroyed()) {
        progressWindow.webContents.send('progress', prog);
      }
    },
    () => {
      if (!progressWindow.isDestroyed()) {
        progressWindow.close();
      }
      
      dialog.showMessageBox(mainWindow || undefined, {
        type: 'info',
        title: 'Ready to Install',
        message: 'Download complete!',
        detail: 'The app will now close to install the update. Please follow the installation prompts.',
        buttons: ['Install Now']
      }).then(() => {
        log.info('Launching installer: ' + destPath);
        try {
          const child = spawn(destPath, [], {
            detached: true,
            stdio: 'ignore'
          });
          child.unref();
          log.info('Quitting app for update installation...');
          app.quit();
        } catch (e) {
          log.error('Failed to launch installer: ' + e.message);
          dialog.showErrorBox('Installation Failed', 'Failed to start the installer: ' + e.message + '\n\nPlease run the installer manually from:\n' + destPath);
        }
      });
    },
    (err) => {
      if (!progressWindow.isDestroyed()) {
        progressWindow.close();
      }
      log.error('Auto update failed: ' + err.message);
      dialog.showErrorBox('Download Failed', 'Could not download the update automatically.\n\nError: ' + err.message + '\n\nPlease try updating manually or check your internet connection.');
    }
  );
}

function isNewerVersion(latest, current) {
  const parse = (v) => v.replace(/^v/, '').split('.').map(Number);
  const a = parse(latest);
  const b = parse(current);
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const v1 = a[i] || 0;
    const v2 = b[i] || 0;
    if (v1 > v2) return true;
    if (v1 < v2) return false;
  }
  return false;
}

function checkForUpdates(manual = false) {
  log.info('Checking for updates...');
  const updateUrl = 'https://raw.githubusercontent.com/m3iK18dp/EveryThingDownloader-Tool/main/update.json'; 

  const req = https.get(updateUrl, { timeout: 10000 }, (res) => {
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('end', () => {
      try {
        if (res.statusCode !== 200) {
          throw new Error('HTTP Status ' + res.statusCode);
        }
        const info = JSON.parse(data);
        const latestVersion = info.version;
        const currentVersion = app.getVersion();
        
        if (isNewerVersion(latestVersion, currentVersion)) {
          dialog.showMessageBox(mainWindow, {
            type: 'info',
            title: 'Update Available',
            message: `A new version (${latestVersion}) is available!`,
            detail: info.changelog || 'No release notes available.',
            buttons: ['Update Automatically (Recommended)', 'Download Manually', 'Later'],
            defaultId: 0,
            cancelId: 2
          }).then(({ response }) => {
            if (response === 0 && info.url) {
              startAutoUpdate(info.url, latestVersion);
            } else if (response === 1 && info.url) {
              shell.openExternal(info.url);
            }
          });
        } else {
          if (manual) {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'No Updates',
              message: 'You are running the latest version.',
              detail: `Current Version: ${currentVersion}`,
              buttons: ['OK']
            });
          }
        }
      } catch (err) {
        log.error('Update check failed parse:', err.message);
        if (manual) {
          dialog.showErrorBox('Update Check Failed', `Could not check for updates.\n\nError: ${err.message}`);
        }
      }
    });
  });
  
  req.on('error', (err) => {
    log.error('Update check request error:', err.message);
    if (manual) {
      dialog.showErrorBox('Update Check Failed', `Could not check for updates. Please check your network connection.\n\nError: ${err.message}`);
    }
  });
}

function restartBackendServer() {
  log.info('Restarting backend server...');
  killFlaskServer();
  setTimeout(async () => {
    try {
      await startFlaskServer();
      log.info('Flask server restarted successfully.');
      dialog.showMessageBox(mainWindow, {
        type: 'info',
        title: 'Server Restarted',
        message: 'The internal Flask backend server has been restarted.',
        buttons: ['OK']
      });
    } catch (err) {
      log.error('Failed to restart Flask server:', err);
      dialog.showErrorBox('Restart Failed', `Failed to restart backend server.\n\nError: ${err.message}`);
    }
  }, 1000);
}

// ─── System Tray ─────────────────────────────────────────────────────────────

function buildTrayMenu() {
  const autoStart = app.getLoginItemSettings().openAtLogin;

  const contextMenu = Menu.buildFromTemplate([
    {
      label: `✨ ${APP_NAME} (v${app.getVersion()})`,
      enabled: false,
    },
    { type: 'separator' },
    {
      label: '📥 Open Application',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      },
    },
    {
      label: '🌐 Open in Default Browser',
      click: () => {
        shell.openExternal(`http://127.0.0.1:${serverPort}/`);
      },
    },
    {
      label: '📂 Open Downloads Folder',
      click: () => {
        const downloadsDir = app.isPackaged
          ? path.join(process.resourcesPath, 'downloads')
          : path.join(__dirname, '..', 'downloads');
        shell.openPath(downloadsDir);
      },
    },
    { type: 'separator' },
    {
      label: autoStart ? '⚙️ Start with Windows (Enabled)' : '⚙️ Start with Windows (Disabled)',
      click: () => {
        const currentSettings = app.getLoginItemSettings();
        const nextState = !currentSettings.openAtLogin;
        app.setLoginItemSettings({
          openAtLogin: nextState,
          path: process.execPath,
        });
        buildTrayMenu();
      },
    },
    {
      label: '🔄 Restart Backend Server',
      click: () => {
        restartBackendServer();
      },
    },
    {
      label: '🔔 Check for Updates',
      click: () => {
        checkForUpdates(true);
      },
    },
    { type: 'separator' },
    {
      label: '🛑 Quit',
      click: () => {
        app.isQuitting = true;
        app.quit();
      },
    },
  ]);

  if (tray) {
    tray.setContextMenu(contextMenu);
  }
  return contextMenu;
}

function createTray() {
  const icon = getAppIcon();
  tray = new Tray(icon.isEmpty() ? nativeImage.createEmpty() : icon);
  tray.setToolTip(APP_NAME);

  buildTrayMenu();

  tray.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

// ─── IPC Handlers ─────────────────────────────────────────────────────────────

ipcMain.handle('get-app-version', () => app.getVersion());
ipcMain.handle('get-server-port', () => serverPort);

ipcMain.on('window-minimize', () => mainWindow?.minimize());
ipcMain.on('window-maximize', () => {
  if (mainWindow?.isMaximized()) mainWindow.unmaximize();
  else mainWindow?.maximize();
});
ipcMain.on('window-close', () => {
  app.isQuitting = false;
  mainWindow?.close();
});

ipcMain.on('open-downloads-folder', () => {
  const downloadsDir = app.isPackaged
    ? path.join(process.resourcesPath, 'downloads')
    : path.join(__dirname, '..', 'downloads');
  shell.openPath(downloadsDir);
});

// ─── Remove native menu bar + register keyboard shortcuts ────────────────────
// Native menus clash with the dark web UI and don't support SVG.
// All actions remain accessible via tray right-click and shortcuts below.

function buildAppMenu() {
  // Wipe the native menu bar entirely
  Menu.setApplicationMenu(null);
}

function setupKeyboardShortcuts() {
  // Reload page
  globalShortcut.register('CmdOrCtrl+R', () => mainWindow?.reload());

  // Navigate home
  globalShortcut.register('CmdOrCtrl+H', () =>
    mainWindow?.loadURL(`http://127.0.0.1:${serverPort}/`)
  );

  // Open downloads folder
  globalShortcut.register('CmdOrCtrl+Shift+D', () => {
    const dir = app.isPackaged
      ? path.join(process.resourcesPath, 'downloads')
      : path.join(__dirname, '..', 'downloads');
    shell.openPath(dir);
  });

  // Zoom controls
  globalShortcut.register('CmdOrCtrl+=', () => {
    const cur = mainWindow?.webContents.getZoomLevel() ?? 0;
    mainWindow?.webContents.setZoomLevel(cur + 0.5);
  });
  globalShortcut.register('CmdOrCtrl+-', () => {
    const cur = mainWindow?.webContents.getZoomLevel() ?? 0;
    mainWindow?.webContents.setZoomLevel(cur - 0.5);
  });
  globalShortcut.register('CmdOrCtrl+0', () =>
    mainWindow?.webContents.setZoomLevel(0)
  );

  // DevTools (dev mode only)
  if (isDev) {
    globalShortcut.register('F12', () =>
      mainWindow?.webContents.toggleDevTools()
    );
  }
}

// ─── App lifecycle ────────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  // Prevent multiple instances
  if (!app.requestSingleInstanceLock()) {
    app.quit();
    return;
  }

  // Remove native menu bar
  buildAppMenu();
  // Register keyboard shortcuts
  setupKeyboardShortcuts();

  app.on('second-instance', () => {
    if (mainWindow) {
      if (!mainWindow.isVisible()) mainWindow.show();
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  // Show splash immediately
  setTimeout(createSplashWindow, SPLASH_WAIT);

  try {
    await startFlaskServer();
    log.info('Waiting for Flask to be ready…');
    await waitForServer(serverPort);
    serverReady = true;
    log.info(`Flask is ready at http://127.0.0.1:${serverPort}`);

    createMainWindow();
    createTray();

    // If main window already loaded before server was marked ready
    if (mainWindow?.webContents.getURL().includes('127.0.0.1')) {
      showMainWindow();
    }
  } catch (err) {
    log.error('Failed to start:', err);
    if (splashWindow && !splashWindow.isDestroyed()) splashWindow.destroy();
    dialog.showErrorBox(
      APP_NAME + ' – Startup Error',
      `Failed to start the internal server.\n\n${err.message}`
    );
    app.quit();
  }
});

app.on('activate', () => {
  // macOS: re-create window if dock icon clicked
  if (BrowserWindow.getAllWindows().length === 0) createMainWindow();
  else mainWindow?.show();
});

app.on('before-quit', () => {
  app.isQuitting = true;
  killFlaskServer();
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
  killFlaskServer();
});

// Disable navigation to external URLs in the main window
app.on('web-contents-created', (_, contents) => {
  contents.on('will-navigate', (event, url) => {
    if (!url.startsWith(`http://127.0.0.1:${serverPort}`)) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });
});
