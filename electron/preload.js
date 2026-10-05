/**
 * Electron Preload Script
 * Bridges renderer (browser window) with main process securely.
 * Exposes safe APIs via contextBridge.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // App info
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  getServerPort: () => ipcRenderer.invoke('get-server-port'),

  // Window controls
  minimizeWindow: () => ipcRenderer.send('window-minimize'),
  maximizeWindow: () => ipcRenderer.send('window-maximize'),
  setMaximize: (maximize) => ipcRenderer.send('window-maximize-set', maximize),
  closeWindow: () => ipcRenderer.send('window-close'),
  
  // Server status
  onServerReady: (callback) => ipcRenderer.on('server-ready', callback),
  onServerError: (callback) => ipcRenderer.on('server-error', (_, msg) => callback(msg)),

  // Download folder
  openDownloadsFolder: () => ipcRenderer.send('open-downloads-folder'),

  // File & Folder selection dialogs
  selectFile: () => ipcRenderer.invoke('select-file'),
  selectFolder: () => ipcRenderer.invoke('select-folder'),
  saveFile: (options) => ipcRenderer.invoke('save-file', options),
  showItemInFolder: (path) => ipcRenderer.send('show-item-in-folder', path),

  // Clipboard events
  onClipboardLink: (callback) => {
    const subscription = (_, link) => callback(link);
    ipcRenderer.on('clipboard-link', subscription);
    return () => ipcRenderer.removeListener('clipboard-link', subscription);
  },
  resetClipboardCache: () => ipcRenderer.send('reset-clipboard-cache'),

  // Stream referer for CDN bypass
  setStreamReferer: (referer) => ipcRenderer.send('set-stream-referer', referer),
  
  // Platform
  platform: process.platform,
  isElectron: true,
});
