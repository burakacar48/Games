const { app, BrowserWindow, ipcMain, shell, dialog } = require('electron'); // 'dialog' eklendi
const path = require('path');
const { exec } = require('child_process');
const fs = require('fs/promises');
const archiver = require('archiver');
const extract = require('extract-zip');
const fetch = require('electron-fetch').default; // electron-fetch kütüphanesi

// --- LİSANS KONTROL BÖLÜMÜ BAŞLANGICI ---

// Kafe sunucunuzun yerel ağdaki IP adresini buraya girin.
// Test için aynı bilgisayardaysa '127.0.0.1' kalabilir.
const SERVER_IP = '127.0.0.1'; 
const SERVER_URL = `http://${SERVER_IP}:5000`;

// DÜZELTME: getPublicIP fonksiyonu artık client'ta kullanılmıyor. Kaldırılabilir veya boş bırakılabilir.

async function verifyLicense() {
  
  // DÜZELTME: Client artık sadece Flask API'sini çağırıyor
  try {
    const response = await fetch(`${SERVER_URL}/api/internal/check_status`); // IP parametresini kaldırdık
    
    // Yanıtın durumu 200 değilse (yani 403 ise) veya JSON yanıtı 'ok' değilse hata fırlat
    if (response.status !== 200 || (await response.clone().json()).status !== 'ok') {
      const errorData = await response.json();
      
      let reason = errorData.reason || "Bilinmeyen bir sunucu hatası oluştu.";
      let debugMessage = '';

      if (errorData.debug) {
        // Debug bilgilerini okunabilir bir formatta hazırla
        debugMessage = '\n\n--- HATA AYIKLAMA (DEBUG) BİLGİLERİ ---\n';
        debugMessage += `Gelen IP (Client): ${errorData.debug.client_ip_incoming}\n`;
        debugMessage += `DB IP (Kayıtlı): ${errorData.debug.licensed_ip_db}\n`;
        debugMessage += `Gelen HWID: ${errorData.debug.hwid_incoming ? errorData.debug.hwid_incoming.substring(0, 10) + '...' : 'BOŞ'}\n`;
        debugMessage += `DB HWID: ${errorData.debug.hwid_db ? errorData.debug.hwid_db.substring(0, 10) + '...' : 'BOŞ'}\n`;
        debugMessage += `Doğrulama Adımı: ${errorData.debug.validation_step || errorData.debug.activation_status || 'N/A'}`;
      }
      
      throw new Error(reason + debugMessage);
    }
    const data = await response.json();
    return data.status === 'ok';
  } catch (error) {
    console.error('Lisans doğrulaması başarısız:', error.message);
    // Hata mesajını (debug bilgileri dahil) göster
    dialog.showErrorBox('Lisans Hatası', `Ana sunucuya bağlanılamadı veya lisans doğrulaması başarısız oldu. Lütfen kafe yöneticinize başvurun.\n\nHata Detayı: ${error.message}`);
    return false;
  }
}

// --- LİSANS KONTROL BÖLÜMÜ SONU ---

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

async function createWindow() { // Fonksiyonu async olarak güncelledik
  // --- LİSANS KONTROLÜ ÇAĞRISI ---
  try {
      const isLicensed = await verifyLicense(); 
      if (!isLicensed) {
        app.quit(); // Lisans geçerli değilse uygulamayı kapat
        return;
      }
  } catch(e) {
      // getPublicIP'den veya verifyLicense'dan gelen katı hataları göster
      dialog.showErrorBox('Kritik Lisans Hatası', `Uygulama başlatılamıyor.\n\nDetay: ${e.message}`);
      app.quit();
      return;
  }
  // --- KONTROL SONU ---

  const win = new BrowserWindow({
    width: 1280,
    height: 720,
    webPreferences: {
      preload: path.join(__dirname, 'src/preload.js'),
    }
  });

  win.webContents.session.clearCache().then(() => {
    console.log('Önbellek temizlendi.');
  });

  win.loadFile('src/index.html');
  win.maximize();
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

// ... (unzip-save ve zip-save fonksiyonları aynı kalacak)
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


// GÜNCELLENDİ: Oyun başlatma mantığı
ipcMain.on('launch-game', async (event, game) => {
    const data = JSON.parse(game.calistirma_verisi);
    
    if (game.calistirma_tipi === 'exe') {
        // Eğer oyun için özel bir launch_script varsa
        if (game.launch_script && game.launch_script.trim() !== '') {
            try {
                let scriptContent = game.launch_script;
                
                // Değişkenleri script içinde değiştir
                scriptContent = scriptContent.replace(/%EXE_YOLU%/g, data.yol || '');
                scriptContent = scriptContent.replace(/%EXE_ARGS%/g, data.argumanlar || '');
                
                const tempBatPath = path.join(app.getPath('temp'), `launch_${Date.now()}.bat`);
                
                // Geçici .bat dosyasını oluştur
                await fs.writeFile(tempBatPath, scriptContent);
                
                // .bat dosyasını çalıştır
                shell.openPath(tempBatPath);

            } catch (err) {
                console.error("Batch script oluşturulurken veya çalıştırılırken hata:", err);
            }
        } else {
            // Eğer script yoksa, direkt EXE'yi çalıştır
            exec(`"${data.yol}" ${data.argumanlar || ''}`, (err) => { 
                if(err) console.error("EXE çalıştırılırken hata:", err);
            });
        }
    } else if (game.calistirma_tipi === 'steam') {
        shell.openExternal(`steam://run/${data.app_id}`);
    }
});