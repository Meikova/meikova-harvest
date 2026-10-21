/**
 * Electron Main Process — Meikova Harvest
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
  nativeTheme,
} = require('electron');

const path  = require('path');
const http  = require('http');
const net   = require('net');
const fs    = require('fs');
const { spawn, execSync } = require('child_process');

// ─── Configuration ────────────────────────────────────────────────────────────
const APP_NAME    = 'Meikova Harvest';
const DEFAULT_PORT = 18650;
const SPLASH_WAIT  = 600;   // ms before showing splash
const SERVER_TIMEOUT = 60000; // ms to wait for Flask (60 s)
const isDev = process.argv.includes('--dev') || !app.isPackaged;

// Force Windows dark theme for native context menus & common dialogs
nativeTheme.themeSource = 'dark';

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
let serverExitEarly = null;
let startupStderr = '';
let isRestartingServer = false;

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
    const start = Date.now();
    serverExitEarly = (err) => {
      clearInterval(interval);
      serverExitEarly = null;
      reject(err);
    };

    const interval = setInterval(() => {
      if (Date.now() - start > timeoutMs) {
        clearInterval(interval);
        serverExitEarly = null;
        const diag = startupStderr.trim() ? `\n\nServer Diagnostics / Stderr:\n${startupStderr.slice(-1500)}` : '';
        return reject(new Error(`Server did not respond within ${timeoutMs / 1000}s.${diag}`));
      }
      const req = http.get(`http://127.0.0.1:${port}/`, (res) => {
        if (res.statusCode < 500) {
          clearInterval(interval);
          serverExitEarly = null;
          serverReady = true;
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
    const candidates = [
      path.join(process.resourcesPath, binaryName),
      path.join(process.resourcesPath, 'resources', binaryName),
      path.join(__dirname, 'resources', binaryName),
      path.join(app.getAppPath(), '..', 'resources', binaryName),
    ];
    for (const p of candidates) {
      if (fs.existsSync(p)) return p;
    }
    return candidates[0];
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
  if (process.platform === 'win32') {
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
    EVERYTHING_USER_DATA: app.getPath('userData'),
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
    if (!fs.existsSync(serverExe)) {
      throw new Error(`Server executable not found at:\n${serverExe}\n\nPlease reinstall or rebuild the application.`);
    }

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
        'Meikova Harvest Backend Server',
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

  startupStderr = '';
  flaskProcess.stdout?.on('data', (d) => log.info('[Flask]', d.toString().trimEnd()));
  flaskProcess.stderr?.on('data', (d) => {
    const text = d.toString();
    startupStderr += text;
    if (startupStderr.length > 8192) {
      startupStderr = startupStderr.slice(-8192);
    }
    log.warn('[Flask]', text.trimEnd());
  });
  flaskProcess.on('error', (err) => {
    log.error('Flask process error:', err);
    if (!serverReady && typeof serverExitEarly === 'function') {
      serverExitEarly(err);
    }
  });
  flaskProcess.on('exit', (code) => {
    log.info(`Flask exited with code ${code}`);
    flaskProcess = null;
    if (isRestartingServer) {
      return;
    }
    if (!serverReady) {
      const errDetail = startupStderr.trim() || `Process exited with code ${code} without output.`;
      const err = new Error(`Internal server process terminated prematurely (exit code ${code}).\n\nError details:\n${errDetail}`);
      if (typeof serverExitEarly === 'function') {
        serverExitEarly(err);
      }
    } else if (mainWindow && !app.isQuitting) {
      sendAppAlert('SYS // ENGINE DISCONNECTED', 'Máy chủ backend đã dừng. Vui lòng đóng và mở lại ứng dụng.', 'error');
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
    const downloadsDir = getAppDownloadsDir();
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
    try {
      mainWindow.setIcon(getAppIcon());
    } catch (e) {}
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
    try {
      mainWindow.setIcon(getAppIcon());
    } catch (e) {}
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show();
    mainWindow.setAlwaysOnTop(true);
    mainWindow.focus();
    mainWindow.setAlwaysOnTop(false);
    log.info('mainWindow is now visible and brought to front');
  }
}

let customDownloadsDir = null;

function loadCustomDownloadsDir() {
  try {
    const settingsFile = path.join(app.getPath('userData'), 'settings.json');
    if (fs.existsSync(settingsFile)) {
      const data = JSON.parse(fs.readFileSync(settingsFile, 'utf-8'));
      if (data && data.downloadsDir && typeof data.downloadsDir === 'string' && fs.existsSync(data.downloadsDir)) {
        customDownloadsDir = data.downloadsDir;
        log.info(`[Settings] Loaded custom downloads directory: ${customDownloadsDir}`);
      }
    }
  } catch (err) {
    log.warn('[Settings] Failed to load custom downloads directory:', err);
  }
}

function getAppDownloadsDir() {
  if (customDownloadsDir && fs.existsSync(customDownloadsDir)) {
    return customDownloadsDir;
  }
  const userDownloads = app.getPath('downloads');
  const targetDir = path.join(userDownloads, 'MeikovaHarvest');
  try {
    if (!fs.existsSync(targetDir)) {
      fs.mkdirSync(targetDir, { recursive: true });
    }
    return targetDir;
  } catch (_) {
    return userDownloads;
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
        path.join(process.resourcesPath, 'resources'),
        path.join(__dirname, 'resources'),
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

let updateDownloadState = {
  isDownloading: false,
  percent: 0,
  version: '',
  destPath: '',
};
let installOnQuitPath = null;

function sendAppAlert(title, message, type = 'info') {
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (mainWindow.isMinimized()) {
      mainWindow.restore();
    }
    if (!mainWindow.isVisible()) {
      mainWindow.show();
    }
    mainWindow.focus();
    mainWindow.webContents.send('app-alert', { title, message, type });
  } else {
    if (type === 'error') {
      dialog.showErrorBox(title, message);
    } else {
      dialog.showMessageBox({
        type: 'info',
        title,
        message,
        buttons: ['OK'],
      });
    }
  }
}

async function installDownloadedUpdate(destPath) {
  log.info('Preparing to install update from: ' + destPath);
  if (!fs.existsSync(destPath)) {
    log.error('Installer file not found: ' + destPath);
    sendAppAlert('SYS // CÀI ĐẶT THẤT BẠI', 'Không tìm thấy bộ cài đặt cập nhật đã tải về.\n\nVui lòng thử tải lại bản cập nhật.', 'error');
    return;
  }

  // 1. Send graceful shutdown request to Flask backend
  try {
    const shutdownReq = http.request({
      hostname: '127.0.0.1',
      port: serverPort,
      path: '/api/system/shutdown',
      method: 'POST',
      timeout: 1500,
    });
    shutdownReq.on('error', () => {});
    shutdownReq.end();
  } catch (_) {}

  // Wait 400ms for clean SQLite WAL truncate and file handle release
  await new Promise(r => setTimeout(r, 400));
  killFlaskServer();

  try {
    if (process.platform === 'win32') {
      log.info('Launching installer silently via PowerShell on Windows...');
      const escapedPath = destPath.replace(/'/g, "''");
      const psScript = `Start-Sleep -Milliseconds 600; Start-Process -FilePath '${escapedPath}'`;
      const child = spawn('powershell.exe', [
        '-WindowStyle', 'Hidden',
        '-NoProfile',
        '-NonInteractive',
        '-Command',
        psScript
      ], {
        detached: true,
        stdio: 'ignore',
        windowsHide: true,
      });
      child.unref();
    } else if (process.platform === 'darwin') {
      shell.openPath(destPath).then((err) => {
        if (err) {
          log.error('Failed to open DMG: ' + err);
          shell.showItemInFolder(destPath);
        }
      });
    } else {
      // Linux
      if (destPath.endsWith('.AppImage')) {
        try { fs.chmodSync(destPath, 0o755); } catch (_) {}
        const child = spawn('bash', ['-c', `sleep 1 && exec "${destPath}"`], {
          detached: true,
          stdio: 'ignore',
        });
        child.unref();
      } else {
        shell.showItemInFolder(destPath);
      }
    }
    app.isQuitting = true;
    app.quit();
  } catch (e) {
    log.error('Failed to launch installer:', e);
    sendAppAlert('SYS // CÀI ĐẶT THẤT BẠI', `Không thể khởi chạy bộ cài đặt:\n${e.message}`, 'error');
  }
}

function startAutoUpdate(url, version) {
  if (updateDownloadState.isDownloading) {
    log.info('Auto update download already in progress.');
    return;
  }

  log.info(`Starting auto update in background for v${version}. URL: ${url}`);
  updateDownloadState.isDownloading = true;
  updateDownloadState.percent = 0;
  updateDownloadState.version = version;

  let destName = `MeikovaHarvest-Setup-${version}.exe`;
  if (process.platform === 'darwin') {
    destName = `MeikovaHarvest-${version}-${process.arch}.dmg`;
  } else if (process.platform === 'linux') {
    destName = `MeikovaHarvest-${version}-${process.arch}.AppImage`;
  }
  const destPath = path.join(app.getPath('temp'), destName);
  updateDownloadState.destPath = destPath;

  // Notify frontend of download start without blocking the app
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('update-download-progress', {
      status: 'starting',
      percent: 0,
      version: version,
      transferred: '0',
      total: '0',
      speed: '0 KB/s'
    });
  }

  downloadFile(url, destPath, 
    (prog) => {
      updateDownloadState.percent = prog.percent;
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('update-download-progress', {
          status: 'downloading',
          percent: prog.percent,
          transferred: prog.transferred,
          total: prog.total,
          speed: prog.speed || '0 KB/s',
          version: version,
        });
      }
    },
    () => {
      updateDownloadState.isDownloading = false;
      log.info(`Update v${version} successfully downloaded to: ${destPath}`);
      if (mainWindow && !mainWindow.isDestroyed()) {
        if (mainWindow.isMinimized()) mainWindow.restore();
        mainWindow.show();
        mainWindow.focus();
        mainWindow.webContents.send('update-download-progress', {
          status: 'completed',
          percent: 100,
          version: version,
          destPath: destPath,
        });
      }
    },
    (err) => {
      updateDownloadState.isDownloading = false;
      log.error('Auto update download failed:', err.message);
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('update-download-progress', {
          status: 'error',
          error: err.message,
          version: version,
        });
      }
      sendAppAlert('SYS // TẢI BẢN CẬP NHẬT THẤT BẠI', `Không thể tải bản cập nhật tự động.\n\nChi tiết: ${err.message}\n\nVui lòng thử cập nhật thủ công hoặc kiểm tra lại kết nối mạng.`, 'error');
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
  const updateUrl = 'https://raw.githubusercontent.com/Meikova/meikova-harvest-tool/main/update.json'; 

  const req = https.get(updateUrl, {
    timeout: 10000,
    headers: { 'User-Agent': `MeikovaHarvest/${app.getVersion()}` }
  }, (res) => {
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
          let platformUrl = info.url;
          if (info.platforms) {
            const platformKey = process.platform + '_' + process.arch;
            platformUrl = info.platforms[platformKey] || info.platforms[process.platform] || info.url;
          }

          if (mainWindow && !mainWindow.isDestroyed()) {
            if (mainWindow.isMinimized()) mainWindow.restore();
            mainWindow.show();
            mainWindow.focus();
            mainWindow.webContents.send('update-available', {
              version: latestVersion,
              currentVersion: currentVersion,
              changelog: info.changelog || '',
              url: platformUrl
            });
          } else {
            dialog.showMessageBox({
              type: 'info',
              title: 'Update Available',
              message: `A new version (${latestVersion}) is available!`,
              detail: info.changelog || 'No release notes available.',
              buttons: ['Download Manually', 'Later'],
              defaultId: 0,
              cancelId: 1
            }).then(({ response }) => {
              if (response === 0 && platformUrl) {
                shell.openExternal(platformUrl);
              }
            });
          }
        } else {
          if (manual) {
            sendAppAlert('SYS // PHIÊN BẢN MỚI NHẤT', `Bạn đang sử dụng phiên bản mới nhất (v${currentVersion}).`, 'info');
          }
        }
      } catch (err) {
        log.error('Update check failed parse:', err.message);
        if (manual) {
          sendAppAlert('SYS // LỖI KIỂM TRA', `Không thể kiểm tra bản cập nhật.\n\nChi tiết: ${err.message}`, 'error');
        }
      }
    });
  });
  
  req.on('error', (err) => {
    log.error('Update check request error:', err.message);
    if (manual) {
      sendAppAlert('SYS // LỖI KẾT NỐI', `Không thể kết nối đến máy chủ cập nhật. Vui lòng kiểm tra lại đường truyền mạng.\n\nChi tiết: ${err.message}`, 'error');
    }
  });
}

function restartBackendServer() {
  log.info('Restarting backend server...');
  isRestartingServer = true;
  killFlaskServer();
  setTimeout(async () => {
    try {
      await startFlaskServer();
      isRestartingServer = false;
      log.info('Flask server restarted successfully.');
      sendAppAlert('SYS // ENGINE STATUS', 'Máy chủ Flask backend đã được khởi động lại thành công.', 'success');
    } catch (err) {
      isRestartingServer = false;
      log.error('Failed to restart Flask server:', err);
      sendAppAlert('SYS // ENGINE ERROR', `Không thể khởi động lại backend server.\n\nChi tiết: ${err.message}`, 'error');
    }
  }, 1000);
}

// ─── System Tray ─────────────────────────────────────────────────────────────

function getTrayIcon(name) {
  try {
    const candidates = [
      path.join(__dirname, 'resources', 'tray_icons', `${name}.png`),
      path.join(process.resourcesPath, 'tray_icons', `${name}.png`),
      path.join(process.resourcesPath, 'resources', 'tray_icons', `${name}.png`),
      path.join(process.resourcesPath, '..', 'resources', 'tray_icons', `${name}.png`),
    ];
    for (const iconPath of candidates) {
      if (fs.existsSync(iconPath)) {
        const img = nativeImage.createFromPath(iconPath);
        if (!img.isEmpty()) {
          return img.resize({ width: 16, height: 16 });
        }
      }
    }
  } catch (_) {}
  return undefined;
}

function getTrayMainIcon() {
  const isWin = process.platform === 'win32';
  const trayIcon = getTrayIcon('logo');
  if (trayIcon && !trayIcon.isEmpty()) {
    return trayIcon;
  }
  let icon = getAppIcon();
  if (isWin && !icon.isEmpty()) {
    icon = icon.resize({ width: 16, height: 16 });
  }
  return icon;
}

function buildTrayMenu() {
  const autoStart = app.getLoginItemSettings().openAtLogin;

  const contextMenu = Menu.buildFromTemplate([
    {
      label: `${APP_NAME} // v${app.getVersion()}`,
      icon: getTrayIcon('logo'),
      enabled: false,
    },
    { type: 'separator' },
    {
      label: 'Mở Meikova Harvest',
      icon: getTrayIcon('window'),
      click: () => {
        if (mainWindow) {
          if (mainWindow.isMinimized()) mainWindow.restore();
          mainWindow.show();
          mainWindow.focus();
        }
      },
    },
    {
      label: 'Mở trên trình duyệt Web',
      icon: getTrayIcon('browser'),
      click: () => {
        shell.openExternal(`http://127.0.0.1:${serverPort}/`);
      },
    },
    {
      label: 'Mở thư mục tải về',
      icon: getTrayIcon('folder'),
      click: () => {
        const downloadsDir = getAppDownloadsDir();
        shell.openPath(downloadsDir);
      },
    },
    { type: 'separator' },
    {
      label: `Khởi động cùng Windows: ${autoStart ? 'Bật' : 'Tắt'}`,
      icon: getTrayIcon(autoStart ? 'autostart_on' : 'autostart'),
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
      label: 'Khởi động lại Backend Engine',
      icon: getTrayIcon('refresh'),
      click: () => {
        restartBackendServer();
      },
    },
    {
      label: 'Kiểm tra bản cập nhật...',
      icon: getTrayIcon('update'),
      click: () => {
        checkForUpdates(true);
      },
    },
    { type: 'separator' },
    {
      label: 'Thoát ứng dụng',
      icon: getTrayIcon('quit'),
      click: () => {
        app.isQuitting = true;
        destroyTray();
        if (mainWindow) {
          mainWindow.removeAllListeners('close');
          mainWindow.destroy();
        }
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
  let icon = getTrayMainIcon();
  tray = new Tray(icon.isEmpty() ? nativeImage.createEmpty() : icon);
  tray.setToolTip(`${APP_NAME} v${app.getVersion()}`);

  buildTrayMenu();

  tray.on('double-click', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });

  tray.on('click', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
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
  const downloadsDir = getAppDownloadsDir();
  shell.openPath(downloadsDir);
});

ipcMain.on('open-external', (_, url) => {
  if (url && (typeof url === 'string') && (url.startsWith('http://') || url.startsWith('https://'))) {
    shell.openExternal(url);
  }
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

  const defaultDir = getAppDownloadsDir();
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

ipcMain.handle('get-downloads-dir', () => {
  return getAppDownloadsDir();
});

ipcMain.handle('set-downloads-dir', (event, newDir) => {
  if (newDir && typeof newDir === 'string' && fs.existsSync(newDir)) {
    customDownloadsDir = newDir;
    try {
      const settingsFile = path.join(app.getPath('userData'), 'settings.json');
      let currentSettings = {};
      if (fs.existsSync(settingsFile)) {
        currentSettings = JSON.parse(fs.readFileSync(settingsFile, 'utf-8'));
      }
      currentSettings.downloadsDir = newDir;
      fs.writeFileSync(settingsFile, JSON.stringify(currentSettings, null, 2), 'utf-8');
      log.info(`[Settings] Saved custom downloads directory: ${newDir}`);
    } catch (err) {
      log.error('[Settings] Failed to save custom downloads directory:', err);
    }
    return { success: true, dir: customDownloadsDir };
  }
  return { success: false };
});

ipcMain.on('show-item-in-folder', (event, filePath) => {
  if (filePath && fs.existsSync(filePath)) {
    shell.showItemInFolder(filePath);
  }
});

ipcMain.on('open-file', (event, filePath) => {
  if (filePath && fs.existsSync(filePath)) {
    shell.openPath(filePath);
  }
});

// ─── Application Update IPC ──────────────────────────────────────────────────
ipcMain.on('check-for-updates', () => {
  checkForUpdates(true);
});

ipcMain.on('start-auto-update', (event, payload) => {
  const url = (payload && payload.url) || payload;
  const version = (payload && payload.version) || 'latest';
  if (url) {
    startAutoUpdate(url, version);
  }
});

ipcMain.on('install-update-now', () => {
  if (updateDownloadState.destPath) {
    installDownloadedUpdate(updateDownloadState.destPath);
  }
});

ipcMain.on('install-update-on-quit', () => {
  if (updateDownloadState.destPath) {
    installOnQuitPath = updateDownloadState.destPath;
    log.info(`Deferred update registered to install on quit: ${installOnQuitPath}`);
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
    const dir = getAppDownloadsDir();
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
  if (process.platform === 'win32') {
    if (!isDev) {
      app.setAppUserModelId('com.meikova.harvest');
    } else {
      app.setAppUserModelId('com.meikova.harvest.dev');
    }
  }

  // Prevent multiple instances
  if (!app.requestSingleInstanceLock()) {
    app.quit();
    return;
  }

  loadCustomDownloadsDir();

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

function destroyTray() {
  if (tray) {
    try {
      tray.destroy();
    } catch (_) {}
    tray = null;
  }
}

app.on('before-quit', () => {
  app.isQuitting = true;
  destroyTray();
  killFlaskServer();
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
  destroyTray();
  killFlaskServer();

  if (installOnQuitPath && fs.existsSync(installOnQuitPath)) {
    log.info('Executing deferred update installer on quit: ' + installOnQuitPath);
    try {
      if (process.platform === 'win32') {
        const escapedPath = installOnQuitPath.replace(/'/g, "''");
        const psScript = `Start-Sleep -Milliseconds 600; Start-Process -FilePath '${escapedPath}'`;
        const child = spawn('powershell.exe', [
          '-WindowStyle', 'Hidden',
          '-NoProfile',
          '-NonInteractive',
          '-Command',
          psScript
        ], {
          detached: true,
          stdio: 'ignore',
          windowsHide: true,
        });
        child.unref();
      } else if (process.platform === 'darwin') {
        shell.openPath(installOnQuitPath);
      } else if (installOnQuitPath.endsWith('.AppImage')) {
        try { fs.chmodSync(installOnQuitPath, 0o755); } catch (_) {}
        const child = spawn('bash', ['-c', `sleep 1 && exec "${installOnQuitPath}"`], {
          detached: true,
          stdio: 'ignore',
        });
        child.unref();
      }
    } catch (err) {
      log.error('Failed to trigger deferred installer on quit:', err);
    }
  }
});
