const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  launchGame: (game) => ipcRenderer.send('launch-game', game),
  unzipSave: (args) => ipcRenderer.invoke('unzip-save', args),
  zipSave: (args) => ipcRenderer.invoke('zip-save', args)
});