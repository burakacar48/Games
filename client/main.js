const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const { exec } = require('child_process');
const fs = require('fs/promises');
const archiver = require('archiver');
const extract = require('extract-zip');

function resolvePath(filePath) {
    if (!filePath) return null;
    const envVarMatch = filePath.match(/%([^%]+)%/);
    if (envVarMatch) {
        const envVar = envVarMatch[1];
        const resolved = process.env[envVar];
        if (resolved) {
            return filePath.replace(`%${envVar}%`, resolved);
        }
    }
    return filePath;
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 720,
    webPreferences: {
      preload: path.join(__dirname, 'src/preload.js'),

      // ! --- GEÇİCİ TEST KODU --- !
      // Bu satır, istemcinin sunucuyla konuşmasını engelleyen
      // CORS güvenlik duvarını devre dışı bırakır. 
      // ! --- TEST KODU BİTİŞİ --- !
    }
  });
  win.loadFile('src/index.html');
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

// Geri kalan tüm ipcMain fonksiyonları aynı...
ipcMain.handle('unzip-save', async (event, { saveDataBuffer, savePath }) => {
    const resolvedPath = resolvePath(savePath);
    if (!resolvedPath) return { success: false, error: 'Geçersiz save yolu.' };
    const tempZipPath = path.join(app.getPath('temp'), `save_${Date.now()}.zip`);
    try {
        const buffer = Buffer.from(saveDataBuffer);
        await fs.writeFile(tempZipPath, buffer);
        await fs.rm(resolvedPath, { recursive: true, force: true }).catch(() => {});
        await fs.mkdir(path.dirname(resolvedPath), { recursive: true });
        await extract(tempZipPath, { dir: resolvedPath });
        await fs.unlink(tempZipPath);
        return { success: true };
    } catch (error) {
        return { success: false, error: error.message };
    }
});

ipcMain.handle('zip-save', async (event, { savePath }) => {
    const resolvedPath = resolvePath(savePath);
    if (!resolvedPath) return { success: false, error: 'Geçersiz save yolu.' };
    try {
        await fs.access(resolvedPath);
        const tempZipPath = path.join(app.getPath('temp'), `upload_${Date.now()}.zip`);
        const output = require('fs').createWriteStream(tempZipPath);
        const archive = archiver('zip', { zlib: { level: 9 } });
        await new Promise((resolve, reject) => {
            output.on('close', resolve);
            archive.on('error', reject);
            archive.pipe(output);
            archive.directory(resolvedPath, false);
            archive.finalize();
        });
        const buffer = await fs.readFile(tempZipPath);
        await fs.unlink(tempZipPath);
        return { success: true, data: buffer };
    } catch (error) {
        if (error.code === 'ENOENT') {
            return { success: false, error: 'Kaydedilecek yerel save dosyası bulunamadı.' };
        }
        return { success: false, error: 'Dosyalar zip\'lenirken bir hata oluştu.' };
    }
});

ipcMain.on('launch-game', (event, game) => {
    const data = JSON.parse(game.calistirma_verisi);
    switch (game.calistirma_tipi) {
        case 'exe':
            exec(`"${data.yol}" ${data.argumanlar || ''}`, (err) => { if(err) console.error(err) });
            break;
        case 'steam':
            shell.openExternal(`steam://run/${data.app_id}`);
            break;
        case 'script':
            data.komutlar.forEach(cmd => exec(cmd, (err) => { if(err) console.error(err) }));
            break;
    }
});