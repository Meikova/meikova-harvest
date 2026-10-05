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
  clipboard,
  session,
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

// Suppress internal Chromium/DevTools protocol warnings (like Autofill.enable failed)
app.commandLine.appendSwitch('log-level', '3');
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');

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
  if (isDev && process.platform === 'win32') {
    try {
      const netstatOut = execSync(`netstat -ano | findstr :${DEFAULT_PORT}`).toString();
      const lines = netstatOut.split('\n').filter(l => l.includes('LISTENING'));
      for (const line of lines) {
        const parts = line.trim().split(/\s+/);
        const pid = parts[parts.length - 1];
        if (pid && pid !== '0' && pid !== String(process.pid)) {
          log.info(`Cleaning up orphan process ${pid} on port ${DEFAULT_PORT}`);
          try { execSync(`taskkill /pid ${pid} /f /t`); } catch (_) {}
        }
      }
    } catch (_) {}
  }

  serverPort = await findFreePort(DEFAULT_PORT);
  log.info(`Starting Flask on port ${serverPort}`);

  const env = {
    ...process.env,
    FLASK_PORT: String(serverPort),
    FLASK_ENV:  isDev ? 'development' : 'production',
    PYTHONUNBUFFERED: '1',
  };

  if (isDev) {
    const venvDir = path.join(__dirname, '..', 'venv');
    const venvScripts = process.platform === 'win32'
      ? path.join(venvDir, 'Scripts')
      : path.join(venvDir, 'bin');
    if (fs.existsSync(venvDir)) {
      env.VIRTUAL_ENV = venvDir;
      env.PATH = `${venvScripts}${path.delimiter}${process.env.PATH || ''}`;
    }
  }

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

// ─── Network Interception & Ad-blocking Guards ─────────────────────────────
let activeStreamReferer = 'https://animevietsub.nl/';

function setupNetworkGuards() {
  ipcMain.on('set-stream-referer', (_, referer) => {
    if (referer && typeof referer === 'string') {
      try {
        const u = new URL(referer);
        activeStreamReferer = u.origin + '/';
      } catch (_) {
        activeStreamReferer = referer;
      }
      log.info(`[Stream] Active stream referer set to: ${activeStreamReferer}`);
    }
  });

  // Intercept and block ad / tracking requests at network level across all sessions
  session.defaultSession.webRequest.onBeforeRequest((details, callback) => {
    // 1. Intercept ads/active to return empty ad configuration, killing pause ads before creation
    if (details.url.includes('/admin/api/ads/active') || details.url.includes('ads/active')) {
      const emptyAds = JSON.stringify({ pauseAd: null, ads: [] });
      return callback({ redirectURL: 'data:application/json;charset=utf-8,' + encodeURIComponent(emptyAds) });
    }
    // 2. Block betting ads, doubleclick, syndication, ad tracking
    if (/bom88|adqc\.net|pagead2|doubleclick|googlesyndication|adservice|popads/i.test(details.url)) {
      return callback({ cancel: true });
    }
    callback({});
  });

  // Rewrite headers for Google CDN requests from player iframe (matches origin token)
  session.defaultSession.webRequest.onBeforeSendHeaders((details, callback) => {
    const currentRef = details.referrer || details.requestHeaders['Referer'] || '';
    if (currentRef && !currentRef.includes('127.0.0.1') && !currentRef.includes('localhost') && !currentRef.includes('googleapiscdn')) {
      try {
        activeStreamReferer = new URL(currentRef).origin + '/';
      } catch (_) {}
    }

    if (details.url.includes('googleapiscdn.com')) {
      let ref = activeStreamReferer || 'https://animevietsub.nl/';
      if (currentRef && !currentRef.includes('127.0.0.1') && !currentRef.includes('localhost') && !currentRef.includes('googleapiscdn')) {
        try {
          ref = new URL(currentRef).origin + '/';
        } catch (_) {}
      }
      details.requestHeaders['Referer'] = ref;
      details.requestHeaders['Origin'] = 'https://storage.googleapiscdn.com';
    }
    callback({ requestHeaders: details.requestHeaders });
  });
}

// ─── Web contents initialization & Ad blocking guards ───────────────────────

app.on('web-contents-created', (_, contents) => {
  if (contents.getType() === 'webview') {
    // For guest webviews: completely deny external popups and ad redirects
    contents.setWindowOpenHandler(({ url }) => {
      log.info(`[Webview] Blocked popup window: ${url}`);
      return { action: 'deny' };
    });

    contents.on('will-navigate', (event, url) => {
      // Prevent webview from navigating to ad/warning pages
      if (url.includes('devtools-warning') || url.includes('adblock-warning') || /ads|bet|bom88|casino|affiliate/i.test(url)) {
        event.preventDefault();
        log.info(`[Webview] Blocked navigation: ${url}`);
      }
    });

    const injectWebviewGuards = () => {
      contents.insertCSS(`
        #avs-pause-ad, .avs-pause-ad, [id*="pause-ad"], [class*="pause-ad"],
        [id*="avs-pause"], [class*="avs-pause"],
        .avs-pause-ad-box, .avs-pause-ad-link, .avs-pause-ad-img, .avs-pause-ad-label,
        .avs-pause-ad-actions, .avs-pause-ad-dismiss, .avs-pause-ad-resume,
        #avs-resume-overlay, #avs-resume-box, .avs-resume-box, [id*="avs-resume"], [class*="avs-resume"],
        #avs-compat-fallback, .avs-warning, .browser-warning, [id*="compat-fallback"],
        .quality-notice, [class*="ads"], [id*="ads"], [class*="banner"], [id*="banner"],
        [id*="devtools"], [class*="devtools"], [id*="adblock"], [class*="adblock"],
        .avs-ads, #avs-ads, .vast-skip-button, .jw-ad-container, [class*="jw-ad"], [id*="jw-ad"],
        iframe[src*="ad"], iframe[src*="bet"], a[href*="bom88"], a[href*="bet"],
        div[style*="z-index: 9999"], div[style*="z-index: 2147483647"] {
          display: none !important;
          visibility: hidden !important;
          opacity: 0 !important;
          pointer-events: none !important;
          height: 0 !important;
          width: 0 !important;
          max-height: 0 !important;
          max-width: 0 !important;
          overflow: hidden !important;
        }
      `).catch(() => {});

      contents.executeJavaScript(`
        (function() {
          // 1. Intercept XHR & fetch for ads/active
          try {
            const origOpen = XMLHttpRequest.prototype.open;
            XMLHttpRequest.prototype.open = function(method, url) {
              if (typeof url === 'string' && (url.includes('ads/active') || url.includes('admin/api/ads'))) {
                this._isAdReq = true;
              }
              return origOpen.apply(this, arguments);
            };
            const origSend = XMLHttpRequest.prototype.send;
            XMLHttpRequest.prototype.send = function() {
              if (this._isAdReq) {
                Object.defineProperty(this, 'readyState', { value: 4 });
                Object.defineProperty(this, 'status', { value: 200 });
                Object.defineProperty(this, 'statusText', { value: 'OK' });
                Object.defineProperty(this, 'responseText', { value: '{"pauseAd":null,"ads":[]}' });
                Object.defineProperty(this, 'response', { value: '{"pauseAd":null,"ads":[]}' });
                if (typeof this.onreadystatechange === 'function') this.onreadystatechange();
                if (typeof this.onload === 'function') this.onload();
                return;
              }
              return origSend.apply(this, arguments);
            };
          } catch(_) {}

          // 2. DOM Scrubber
          const scrub = () => {
            const pad = document.getElementById('avs-pause-ad');
            if (pad) pad.remove();
            const res = document.getElementById('avs-resume-overlay');
            if (res) res.remove();
            const bads = document.querySelectorAll('.avs-pause-ad-box, [id*="pause-ad"], [class*="pause-ad"]');
            bads.forEach(b => b.remove());
          };
          try {
            const obs = new MutationObserver(scrub);
            obs.observe(document.body || document.documentElement, { childList: true, subtree: true });
          } catch(_) {}
          scrub();
          if (typeof jwplayer === 'function') {
            const p = jwplayer('player');
            if (p && p.on) {
              p.on('pause', () => {
                setTimeout(scrub, 10);
                setTimeout(scrub, 60);
              });
            }
          }
          return true;
        })()
      `).catch(() => {});
    };

    contents.on('dom-ready', injectWebviewGuards);
    contents.on('did-finish-load', injectWebviewGuards);
    return;
  }

  contents.setWindowOpenHandler(({ url }) => {
    const isAd = /ads|bet|bom88|casino|affiliate|popads|doubleclick|tracker|game/i.test(url);
    if (isAd) {
      log.info(`[AdBlock] Denied popup window: ${url}`);
      return { action: 'deny' };
    }
    // Block internal download URLs from opening external web browser
    if (url.includes('/api/download/file/')) {
      log.info(`[Download] Prevented external browser navigation for internal URL: ${url}`);
      return { action: 'deny' };
    }
    shell.openExternal(url);
    return { action: 'deny' };
  });

  contents.on('will-navigate', (event, url) => {
    // Prevent any frame from navigating to warning pages
    if (url.includes('devtools-warning') || url.includes('adblock-warning')) {
      event.preventDefault();
      log.info(`[WarningBypass] Blocked frame navigation to warning page: ${url}`);
      return;
    }

    const isMainFrame = (event.frame === contents.mainFrame) || (event.isMainFrame !== false && !event.frame);
    if (isMainFrame) {
      const isLocal = url.startsWith(`http://127.0.0.1:${serverPort}`) || url.startsWith(`http://localhost:${serverPort}`);
      if (!isLocal) {
        event.preventDefault();
        shell.openExternal(url);
      }
    }
  });
});

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
    show: true,
    frame: false,            // Frameless — custom SVG controls injected via JS
    titleBarStyle: 'hidden',
    backgroundColor: '#0a0a0f',
    webPreferences: {
      preload:          path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration:  false,
      webviewTag:       true,
      webSecurity:      false,
    },
    icon:  getAppIcon(),
    title: APP_NAME,
  });

  mainWindow.center();

  // Clear cache in dev mode to guarantee fresh assets are loaded
  if (isDev) {
    session.defaultSession.clearCache().catch(err => log.error('Failed to clear cache:', err));
  }




  // Automatically save files triggered via blob/webview downloads to downloads directory
  session.defaultSession.on('will-download', (event, item, webContents) => {
    const downloadsDir = app.isPackaged
      ? path.join(process.resourcesPath, 'downloads')
      : path.join(__dirname, '..', 'downloads');
    if (!fs.existsSync(downloadsDir)) {
      try { fs.mkdirSync(downloadsDir, { recursive: true }); } catch (_) {}
    }
    const savePath = path.join(downloadsDir, item.getFilename());
    item.setSavePath(savePath);
    log.info(`[Download] Starting file download to: ${savePath}`);
    item.once('done', (e, state) => {
      if (state === 'completed') {
        log.info(`[Download] File successfully saved: ${savePath}`);
      } else {
        log.warn(`[Download] Download ended with state: ${state}`);
      }
    });
  });

  mainWindow.once('ready-to-show', () => {
    log.info('mainWindow ready-to-show triggered');
    showMainWindow();
  });

  setTimeout(() => {
    if (mainWindow && !mainWindow.isVisible()) {
      log.info('Safety timeout: forcing mainWindow.show()');
      showMainWindow();
    }
  }, 2500);

  mainWindow.loadURL(`http://localhost:${serverPort}/`);

  // Global F12 and DevTools shortcut handler: open detached and prevent event from reaching web pages
  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (input.type === 'keyDown' && (input.key === 'F12' || (input.control && input.shift && input.key.toLowerCase() === 'i'))) {
      if (mainWindow.webContents.isDevToolsOpened()) {
        mainWindow.webContents.closeDevTools();
      } else {
        mainWindow.webContents.openDevTools({ mode: 'detach' });
      }
      event.preventDefault();
    }
  });

  mainWindow.webContents.on('did-finish-load', () => {
    log.info('mainWindow did-finish-load triggered');
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
    if (isDev) {
      app.isQuitting = true;
      app.quit();
      return;
    }
    if (!app.isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => { mainWindow = null; });

  mainWindow.on('focus', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      setupKeyboardShortcuts();
    }
  });

  mainWindow.on('blur', () => {
    globalShortcut.unregisterAll();
  });

  // Open DevTools in dev mode (detached window prevents anti-devtools detection)
  if (isDev) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }
}

function showMainWindow() {
  log.info('showMainWindow executed');
  if (splashWindow && !splashWindow.isDestroyed()) {
    try {
      splashWindow.close();
      splashWindow.destroy();
    } catch (e) {}
    splashWindow = null;
  }
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show();
    mainWindow.setAlwaysOnTop(true);
    mainWindow.focus();
    mainWindow.setAlwaysOnTop(false);
    log.info('mainWindow is now visible and brought to front');
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
  
  let destName = 'EveryThingDownloader-Setup-' + version + '.exe';
  if (process.platform === 'darwin') {
    destName = 'EveryThingDownloader-' + version + '-' + process.arch + '.dmg';
  } else if (process.platform === 'linux') {
    destName = 'EveryThingDownloader-' + version + '-' + process.arch + '.AppImage';
  }
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
        detail: process.platform === 'darwin'
          ? 'The update has been downloaded. The app will now close and open the installer disk image.'
          : 'The app will now close to install the update.',
        buttons: ['Install/Open Now']
      }).then(() => {
        log.info('Launching installer: ' + destPath);
        try {
          if (process.platform === 'darwin') {
            shell.openPath(destPath).then((err) => {
              if (err) {
                log.error('Failed to open DMG: ' + err);
                shell.showItemInFolder(destPath);
              }
              app.quit();
            });
          } else if (process.platform === 'linux') {
            if (destPath.endsWith('.AppImage')) {
              try {
                fs.chmodSync(destPath, 0o755);
                log.info('Spawning delayed AppImage launcher on Linux...');
                // Wait 2 seconds (via sleep) to allow graceful exit and avoid port conflicts
                const child = spawn('bash', ['-c', `sleep 2 && exec "${destPath}"`], {
                  detached: true,
                  stdio: 'ignore'
                });
                child.unref();
                app.quit();
              } catch (chmodErr) {
                log.error('Failed to make AppImage executable: ' + chmodErr.message);
                shell.showItemInFolder(destPath);
                app.quit();
              }
            } else {
              shell.showItemInFolder(destPath);
              app.quit();
            }
          } else {
            // Windows
            log.info('Spawning delayed installer launcher on Windows...');
            const appExeName = path.basename(process.execPath);
            // Wait 2 seconds (via ping) to allow graceful exit, then kill any lingering processes, then start installer
            const cmd = 'cmd.exe';
            const args = [
              '/c',
              `ping 127.0.0.1 -n 3 > nul & taskkill /f /im server.exe /t 2>nul & taskkill /f /im "${appExeName}" 2>nul & start "" "${destPath}"`
            ];
            const child = spawn(cmd, args, {
              detached: true,
              stdio: 'ignore',
              shell: true,
              windowsHide: true
            });
            child.unref();
            log.info('Quitting app for update installation...');
            app.quit();
          }
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
            let platformUrl = info.url;
            if (info.platforms) {
              const platformKey = process.platform + '_' + process.arch;
              platformUrl = info.platforms[platformKey] || info.platforms[process.platform] || info.url;
            }
            if (response === 0 && platformUrl) {
              startAutoUpdate(platformUrl, latestVersion);
            } else if (response === 1 && platformUrl) {
              shell.openExternal(platformUrl);
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
        if (!fs.existsSync(downloadsDir)) {
          try {
            fs.mkdirSync(downloadsDir, { recursive: true });
          } catch (e) {
            log.error('Failed to create downloads folder:', e);
          }
        }
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
ipcMain.on('window-maximize-set', (_, maximize) => {
  if (maximize) {
    if (mainWindow && !mainWindow.isMaximized()) mainWindow.maximize();
  } else {
    if (mainWindow && mainWindow.isMaximized()) mainWindow.unmaximize();
  }
});
ipcMain.on('window-close', () => {
  app.isQuitting = false;
  mainWindow?.close();
});

ipcMain.on('open-downloads-folder', () => {
  const downloadsDir = app.isPackaged
    ? path.join(process.resourcesPath, 'downloads')
    : path.join(__dirname, '..', 'downloads');
  if (!fs.existsSync(downloadsDir)) {
    try {
      fs.mkdirSync(downloadsDir, { recursive: true });
    } catch (e) {
      log.error('Failed to create downloads folder:', e);
    }
  }
  shell.openPath(downloadsDir);
});

ipcMain.handle('select-file', async () => {
  if (!mainWindow) return null;
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Select File to Analyze',
    properties: ['openFile'],
    filters: [
      { name: 'All Supported Files', extensions: ['torrent', 'mp4', 'mkv', 'webm', 'avi', 'mp3', 'wav', 'flac', 'm4a', 'jpg', 'png', 'webp'] },
      { name: 'BitTorrent Files (*.torrent)', extensions: ['torrent'] },
      { name: 'Video Files', extensions: ['mp4', 'mkv', 'webm', 'avi', 'mov', 'flv', 'ts', 'wmv'] },
      { name: 'Audio Files', extensions: ['mp3', 'wav', 'flac', 'm4a', 'aac', 'ogg', 'opus'] },
      { name: 'All Files (*.*)', extensions: ['*'] }
    ]
  });
  if (result.canceled || !result.filePaths.length) return null;
  return result.filePaths[0];
});

ipcMain.handle('select-folder', async () => {
  if (!mainWindow) return null;
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Select Folder to Analyze',
    properties: ['openDirectory']
  });
  if (result.canceled || !result.filePaths.length) return null;
  return result.filePaths[0];
});

ipcMain.handle('save-file', async (event, { downloadId, defaultFilename }) => {
  if (!mainWindow) return { canceled: true };

  const defaultDir = app.getPath('downloads');
  const result = await dialog.showSaveDialog(mainWindow, {
    title: 'Save File',
    defaultPath: path.join(defaultDir, defaultFilename || 'download'),
    properties: ['showOverwriteConfirmation']
  });

  if (result.canceled || !result.filePath) {
    return { canceled: true };
  }

  const targetPath = result.filePath;
  try {
    const postData = JSON.stringify({ download_id: downloadId, target_path: targetPath });
    const options = {
      hostname: '127.0.0.1',
      port: serverPort,
      path: '/api/download/save-to-disk',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    };

    const resp = await new Promise((resolve, reject) => {
      const req = http.request(options, (res) => {
        let raw = '';
        res.on('data', chunk => raw += chunk);
        res.on('end', () => {
          try {
            resolve(JSON.parse(raw));
          } catch (e) {
            resolve({ status: 'error', message: raw });
          }
        });
      });
      req.on('error', reject);
      req.write(postData);
      req.end();
    });

    if (resp.status === 'success') {
      log.info(`[Save] File saved successfully to: ${targetPath}`);
      return { success: true, filePath: targetPath };
    } else {
      throw new Error(resp.message || 'Server failed to save file');
    }
  } catch (err) {
    log.error('[Save] Save to disk error:', err);
    return { success: false, error: err.message };
  }
});

ipcMain.on('show-item-in-folder', (event, filePath) => {
  if (filePath && fs.existsSync(filePath)) {
    shell.showItemInFolder(filePath);
  }
});

// ─── Remove native menu bar + register keyboard shortcuts ────────────────────
// Native menus clash with the dark web UI and don't support SVG.
// All actions remain accessible via tray right-click and shortcuts below.

function buildAppMenu() {
  // Wipe the native menu bar entirely
  Menu.setApplicationMenu(null);
}

function setupKeyboardShortcuts() {
  // Unregister first to avoid double registration
  globalShortcut.unregisterAll();

  // Reload page (ignoring cache)
  globalShortcut.register('CmdOrCtrl+R', () => mainWindow?.webContents.reloadIgnoringCache());
  globalShortcut.register('F5', () => mainWindow?.webContents.reloadIgnoringCache());

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

  // DevTools (dev mode only — detached window prevents anti-devtools detection)
  if (isDev) {
    globalShortcut.register('F12', () => {
      if (mainWindow?.webContents.isDevToolsOpened()) {
        mainWindow.webContents.closeDevTools();
      } else {
        mainWindow?.webContents.openDevTools({ mode: 'detach' });
      }
    });
  }
}

// ─── Clipboard Monitoring ──────────────────────────────────────────────────────

function isValidVideoUrl(text) {
  if (!text) return false;
  try {
    const url = new URL(text.trim());
    const hostname = url.hostname.toLowerCase();
    const supportedDomains = [
      'youtube.com', 'youtu.be', 'tiktok.com', 'facebook.com', 'fb.watch',
      'instagram.com', 'twitter.com', 'x.com', 'reddit.com', 'threads.net',
      'pinterest.com', 'pin.it'
    ];
    if (supportedDomains.some(domain => hostname.includes(domain))) {
      return true;
    }
    const pathname = url.pathname.toLowerCase();
    const directMediaExtensions = ['.mp4', '.m4v', '.webm', '.mkv', '.mov', '.avi', '.mp3', '.wav', '.m4a', '.aac', '.ogg'];
    if (directMediaExtensions.some(ext => pathname.endsWith(ext))) {
      return true;
    }
  } catch (e) {}
  return false;
}

let lastClipboardText = '';
function startClipboardMonitoring() {
  setInterval(() => {
    if (!mainWindow || mainWindow.isDestroyed()) return;
    try {
      const text = clipboard.readText().trim();
      if (text && text !== lastClipboardText && isValidVideoUrl(text)) {
        lastClipboardText = text;
        mainWindow.webContents.send('clipboard-link', text);
      }
    } catch (e) {
      log.error('Clipboard monitoring error:', e);
    }
  }, 1500);
}

ipcMain.on('reset-clipboard-cache', () => {
  lastClipboardText = '';
});

// ─── App lifecycle ────────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  // Prevent multiple instances
  if (!app.requestSingleInstanceLock()) {
    app.quit();
    return;
  }

  // Set up network-level ad blocking and CDN referer header rewriting early
  setupNetworkGuards();

  // Remove native menu bar
  buildAppMenu();

  app.on('second-instance', () => {
    if (mainWindow) {
      if (!mainWindow.isVisible()) mainWindow.show();
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  // Show splash immediately (only in production)
  if (!isDev) {
    setTimeout(createSplashWindow, SPLASH_WAIT);
  }

  try {
    await startFlaskServer();
    log.info('Waiting for Flask to be ready…');
    await waitForServer(serverPort);
    serverReady = true;
    log.info(`Flask is ready at http://127.0.0.1:${serverPort}`);

    createMainWindow();
    createTray();
    startClipboardMonitoring();

    // If main window already loaded before server was marked ready
    if (mainWindow?.webContents.getURL().includes('localhost') || mainWindow?.webContents.getURL().includes('127.0.0.1')) {
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
