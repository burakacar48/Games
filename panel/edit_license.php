<?php
ini_set('display_errors', 1);
error_reporting(E_ALL);

$license_id = filter_input(INPUT_GET, 'id', FILTER_VALIDATE_INT);
if (!$license_id) {
    echo "Geçersiz Lisans ID.";
    exit;
}

$form_err = $form_success = "";
$license = null;

// Mevcut lisans ve MÜŞTERİ bilgilerini çek
// SELECT SORGUSU GÜNCELLENDİ: address, city, district eklendi
// ÇÖZÜM: Bu sorgu, artık veritabanı düzeltildikten sonra hata vermeyecektir.
$sql_select = "SELECT l.*, c.id as customer_id, c.name as customer_name, c.email, c.phone, c.company, c.address, c.city, c.district, l.id as license_id, l.licensed_ip, l.hwid FROM licenses l JOIN customers c ON l.customer_id = c.id WHERE l.id = ?";
if ($stmt_select = $mysqli->prepare($sql_select)) {
    $stmt_select->bind_param("i", $license_id);
    if ($stmt_select->execute()) {
        $result = $stmt_select->get_result();
        if ($result->num_rows == 1) {
            $license = $result->fetch_assoc();
        } else { 
            echo "Lisans bulunamadı.";
            exit; 
        }
    }
    $stmt_select->close();
}

if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $action = $_POST['action'] ?? '';

    if ($action == 'update_customer_details') {
        $customer_id_update = $license['customer_id'];
        $name = trim($_POST['name']);
        $email = trim($_POST['email']);
        $phone = trim($_POST['phone']);
        $company = trim($_POST['company']);
        // YENİ EKLENEN ALANLAR ALINIYOR
        $address = trim($_POST['address']);
        $city = trim($_POST['city']);
        $district = trim($_POST['district']);
        
        $status_toggle = $_POST['status_toggle'];
        $licensed_ip = trim($_POST['licensed_ip']); // IP adresi alınıyor
        
        // Pasif seçiliyse 'cancelled' olarak ayarla, aksi takdirde 'active'
        $db_status = ($status_toggle === 'passive') ? 'cancelled' : 'active';

        if (empty($name)) {
            $form_err = "Müşteri adı boş bırakılamaz.";
        } else {
            // Müşteri bilgilerini güncelle
            // UPDATE SORGUSU GÜNCELLENDİ: address, city, district eklendi
            $sql_cust = "UPDATE customers SET name = ?, email = ?, phone = ?, company = ?, address = ?, city = ?, district = ? WHERE id = ?";
            if ($stmt_cust = $mysqli->prepare($sql_cust)) {
                // BAĞLAMANIN GÜNCELLENMESİ: sssssssi
                $stmt_cust->bind_param("sssssssi", $name, $email, $phone, $company, $address, $city, $district, $customer_id_update);
                $stmt_cust->execute();
                $stmt_cust->close();
            }
            
            // Lisans durumunu ve IP adresini güncelle
            $sql_lic = "UPDATE licenses SET status = ?, licensed_ip = ? WHERE id = ?";
             if ($stmt_lic = $mysqli->prepare($sql_lic)) {
                $stmt_lic->bind_param("ssi", $db_status, $licensed_ip, $license_id);
                $stmt_lic->execute();
                $stmt_lic->close();
            }

            $form_success = "Müşteri bilgileri ve lisans durumu başarıyla güncellendi.";
            $license['customer_name'] = $name; // Local update
            $license['status'] = $db_status; // Local update
        }
    }
    elseif ($action == 'reset_hwid') {
        // HWID sıfırlama işlemi
        $sql = "UPDATE licenses SET hwid = NULL, status = 'pending' WHERE id = ?";
        if ($stmt = $mysqli->prepare($sql)) {
            $stmt->bind_param("i", $license_id);
            if ($stmt->execute()) {
                $form_success = "HWID başarıyla sıfırlandı. Lisans durumu 'Beklemede' olarak güncellendi.";
            } else {
                $form_err = "HWID sıfırlanırken bir hata oluştu: " . $stmt->error;
            }
            $stmt->close();
        }
    } 
    elseif ($action == 'extend_license') {
        $extension_period = filter_input(INPUT_POST, 'extension_period', FILTER_VALIDATE_INT);
        
        if (!$extension_period || $extension_period < 1 || $extension_period > 3) {
            $form_err = "Geçersiz uzatma süresi seçildi.";
        } else {
            $current_end_date = $license['end_date'];
            $date = new DateTime($current_end_date);
            $date->modify("+{$extension_period} year");
            // Saniye bilgisini koruyarak tam yıl ekle
            $new_end_date = $date->format('Y-m-d H:i:s'); 

            // Veritabanını güncelle
            $sql = "UPDATE licenses SET end_date = ?, status = 'active' WHERE id = ?";
            if ($stmt = $mysqli->prepare($sql)) {
                $stmt->bind_param("si", $new_end_date, $license_id);
                if ($stmt->execute()) {
                    $form_success = "Lisans süresi başarıyla {$extension_period} YIL uzatıldı. Yeni bitiş: " . date("d.m.Y H:i", strtotime($new_end_date));
                    $license['end_date'] = $new_end_date;
                    $license['status'] = 'active'; 
                } else {
                    $form_err = "Uzatma sırasında bir hata oluştu: " . $stmt->error;
                }
                $stmt->close();
            }
        }
    }
    
    // İşlem sonrası tüm bilgileri yeniden çek
    // SELECT SORGUSU GÜNCELLENDİ: c.address, c.city, c.district çekiliyor
    if ($stmt_select = $mysqli->prepare($sql_select)) {
        $stmt_select->bind_param("i", $license_id);
        if ($stmt_select->execute()) {
            $result = $stmt_select->get_result();
            if ($result->num_rows == 1) {
                $license = $result->fetch_assoc();
            }
        }
        $stmt_select->close();
    }
}

if ($license === null) {
     echo "Lisans bilgileri yüklenirken kritik hata oluştu.";
     exit;
}

// Lisans durumunu stilize etmek için yardımcı fonksiyon
function getStatusBadge($status) {
    // pending durumunu active gibi kabul et, expired ve cancelled durumlarını pasif gibi
    if ($status === 'active' || $status === 'pending') {
        return '<span class="px-3 py-1 text-sm font-semibold rounded-full bg-green-500/20 text-green-400">AKTİF</span>';
    } elseif ($status === 'expired') {
        return '<span class="px-3 py-1 text-sm font-semibold rounded-full bg-red-500/20 text-red-400">SÜRESİ DOLDU</span>';
    } elseif ($status === 'cancelled') {
        return '<span class="px-3 py-1 text-sm font-semibold rounded-full bg-slate-500/20 text-slate-400">İPTAL EDİLDİ</span>';
    } else {
        return '<span class="px-3 py-1 text-sm font-semibold rounded-full bg-slate-500/20 text-slate-400">BİLİNMİYOR</span>';
    }
}
?>

<style>
/* Modal stilleri - KARARTMA EFEKTİ KALDIRILDI */
.extend-modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    /* Karartma kaldırıldı */
    background-color: transparent; 
    backdrop-filter: none;
    
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 9999;
    transition: opacity 0.3s ease;
}
.extend-modal-content {
    background-color: #1e293b; /* slate-800 */
    border: 1px solid #475569; /* slate-600 */
    border-radius: 12px;
    padding: 30px;
    width: 90%;
    max-width: 400px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
    color: #e2e8f0;
    position: relative;
}
.close-modal-btn {
    position: absolute;
    top: 10px;
    right: 10px;
    font-size: 24px;
    cursor: pointer;
    color: #94a3b8;
    transition: color 0.2s;
}
.close-modal-btn:hover {
    color: #f87171;
}
</style>

<div>
    <h3 class="text-xl font-bold mb-6 text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600">
        Lisans ve Müşteri Düzenle: <?php echo htmlspecialchars($license['customer_name']); ?>
    </h3>
    
    <?php 
    if(!empty($form_err)) echo '<div class="bg-red-500/10 text-red-400 border border-red-500/20 p-3 rounded-lg mb-4 text-sm">' . $form_err . '</div>';
    if(!empty($form_success)) echo '<div class="bg-green-500/10 text-green-400 border border-green-500/20 p-3 rounded-lg mb-4 text-sm">' . $form_success . '</div>';
    ?>

    <form action="index.php?tab=edit_license&id=<?php echo $license_id; ?>" method="post" class="mb-8" id="main-update-form">
        <input type="hidden" name="action" value="update_customer_details">

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            <div class="md:col-span-2">
                <h4 class="text-lg font-semibold text-slate-300 mb-4 border-b border-slate-700/50 pb-2">Müşteri Bilgileri</h4>
            </div>
            
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Müşteri Adı (*)</label>
                <input type="text" name="name" value="<?php echo htmlspecialchars($license['customer_name'] ?? ''); ?>" required class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Email</label>
                <input type="email" name="email" value="<?php echo htmlspecialchars($license['email'] ?? ''); ?>" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Telefon</label>
                <input type="tel" name="phone" value="<?php echo htmlspecialchars($license['phone'] ?? ''); ?>" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Şirket / Kafe Adı</label>
                <input type="text" name="company" value="<?php echo htmlspecialchars($license['company'] ?? ''); ?>" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">İl</label>
                <input type="text" name="city" value="<?php echo htmlspecialchars($license['city'] ?? ''); ?>" placeholder="Şehir Adı" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">İlçe</label>
                <input type="text" name="district" value="<?php echo htmlspecialchars($license['district'] ?? ''); ?>" placeholder="İlçe Adı" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
             <div class="md:col-span-2">
                <label class="block text-sm font-medium text-slate-300 mb-2">Adres</label>
                <textarea name="address" rows="3" placeholder="Açık Adres Bilgisi" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"><?php echo htmlspecialchars($license['address'] ?? ''); ?></textarea>
            </div>
            <div class="md:col-span-2">
                 <h4 class="text-lg font-semibold text-slate-300 mb-4 border-b border-slate-700/50 pb-2 pt-4">Lisans Bilgileri</h4>
            </div>

            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Lisans Anahtarı</label>
                <input type="text" readonly value="<?php echo htmlspecialchars($license['license_key'] ?? ''); ?>" class="w-full px-4 py-2.5 bg-slate-900/70 border border-slate-700 rounded-lg text-slate-400" />
            </div>
            
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Durum Değiştir</label>
                <select name="status_toggle" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition">
                    <option value="active" <?php echo ($license['status'] == 'active' || $license['status'] == 'pending') ? 'selected' : ''; ?>>Aktif Yap</option>
                    <option value="passive" <?php echo ($license['status'] == 'expired' || $license['status'] == 'cancelled') ? 'selected' : ''; ?>>Pasif Yap (İptal Et)</option>
                </select>
            </div>
            
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Başlangıç Tarihi</label>
                <input type="text" readonly value="<?php echo date("d.m.Y H:i", strtotime($license['start_date'])); ?>" class="w-full px-4 py-2.5 bg-slate-900/70 border border-slate-700 rounded-lg text-white" />
            </div>
            
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Mevcut Bitiş Tarihi</label>
                <input type="text" readonly value="<?php echo date("d.m.Y H:i", strtotime($license['end_date'])); ?>" class="w-full px-4 py-2.5 bg-slate-900/70 border border-slate-700 rounded-lg text-white" />
            </div>

            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Mevcut Lisans Durumu</label>
                <div class="w-full px-4 py-2.5 bg-slate-900/70 border border-slate-700 rounded-lg flex items-center h-[46px]">
                    <?php echo getStatusBadge($license['status']); ?>
                </div>
            </div>
            
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Anakart Seri Numarası (HWID)</label>
                <input type="text" readonly name="hwid_display" value="<?php echo htmlspecialchars($license['hwid'] ?? 'Henüz atanmamış'); ?>" class="w-full px-4 py-2.5 bg-slate-900/70 border border-slate-700 rounded-lg text-slate-400" />
            </div>
            
            <div class="md:col-span-2">
                <label class="block text-sm font-medium text-slate-300 mb-2">Kilitlenecek IP Adresi</label>
                <input type="text" name="licensed_ip" value="<?php echo htmlspecialchars($license['licensed_ip'] ?? ''); ?>" placeholder="Örn: 192.168.1.10 (Boş bırakılırsa IP kontrolü yapılmaz)" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            
        </div>
    </form>
    
    <div class="flex items-center justify-between gap-2 py-3 border-t border-slate-700/50">
        
        <div class="flex items-center gap-2">
            
            <button type="submit" form="main-update-form" class="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg font-semibold hover:from-blue-600 hover:to-purple-700 transition transform hover:scale-[1.02] shadow-lg">
                <i data-lucide="save" class="w-4 h-4"></i>
                <span>Bilgileri Güncelle</span>
            </button>
            
            <form action="index.php?tab=edit_license&id=<?php echo $license_id; ?>" method="post" class="m-0 p-0 flex items-center">
                <button type="submit" name="action" value="reset_hwid" class="flex items-center space-x-2 px-6 py-3 bg-orange-500/20 text-orange-400 border border-orange-500/30 rounded-lg font-semibold hover:bg-orange-500/30 transition" onclick="return confirm('Bu lisansın donanım kaydını sıfırlamak istediğinizden emin misiniz?');">
                    <i data-lucide="rotate-ccw" class="w-4 h-4"></i>
                    <span>HWID Sıfırla</span>
                </button>
            </form>
            
            <button type="button" onclick="document.getElementById('extendModal').style.display='flex';" class="flex items-center space-x-2 px-6 py-3 bg-green-500/20 text-green-400 border border-green-500/30 rounded-lg font-semibold hover:bg-green-500/30 transition">
                <i data-lucide="clock" class="w-4 h-4"></i>
                <span>Süreyi Uzat</span>
            </button>

        </div>
        
        <a href="index.php?tab=customers" class="flex items-center space-x-2 px-6 py-3 bg-slate-700/50 rounded-lg font-semibold hover:bg-slate-600/50 transition">
            <i data-lucide="arrow-left" class="w-4 h-4"></i>
            <span>Geri</span>
        </a>
    </div>

    <div id="extendModal" class="extend-modal-overlay hidden" style="display: none;">
        <div class="extend-modal-content">
            <span class="close-modal-btn" onclick="document.getElementById('extendModal').style.display='none';">&times;</span>
            <h4 class="text-xl font-bold mb-5">Lisans Süresi Uzatma</h4>
            
            <form action="index.php?tab=edit_license&id=<?php echo $license_id; ?>" method="post">
                <input type="hidden" name="action" value="extend_license">
                <p class="text-slate-400 mb-6">Mevcut bitiş tarihi **<?php echo date("d.m.Y H:i", strtotime($license['end_date'])); ?>** üzerine eklenecek süreyi seçin:</p>
                
                <div class="grid grid-cols-3 gap-3">
                    <?php
                    $periods = [1, 2, 3];
                    foreach ($periods as $p) {
                        echo '<button type="submit" name="extension_period" value="' . $p . '" 
                                class="flex flex-col items-center justify-center p-4 h-24 bg-slate-900/50 border border-slate-700 rounded-lg text-white font-semibold hover:bg-green-500/30 hover:border-green-500 transition"
                                onclick="return confirm(\'Lisans süresi ' . $p . ' YIL uzatılacaktır. Onaylıyor musunuz?\');">
                                <span class="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-green-600">' . $p . '</span>
                                <span class="text-sm">YIL UZAT</span>
                              </button>';
                    }
                    ?>
                </div>
            </form>
        </div>
    </div>
</div>

<script>
    // Modal açma/kapama işlevleri
    document.addEventListener('DOMContentLoaded', function() {
        const modal = document.getElementById('extendModal');
        const openBtn = document.querySelector('button[onclick*="extendModal"]'); 
        
        if(openBtn) {
            openBtn.onclick = function() {
                modal.style.display = 'flex';
            }
        }
        
        modal.addEventListener('click', function(e) {
            if (e.target.id === 'extendModal') { 
                modal.style.display = 'none';
            }
        });
    });
</script>