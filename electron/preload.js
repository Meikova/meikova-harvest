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

  // Clipboard events
  onClipboardLink: (callback) => {
    const subscription = (_, link) => callback(link);
    ipcRenderer.on('clipboard-link', subscription);
    return () => ipcRenderer.removeListener('clipboard-link', subscription);
  },
  resetClipboardCache: () => ipcRenderer.send('reset-clipboard-cache'),
  
  // Platform
  platform: process.platform,
  isElectron: true,
});
