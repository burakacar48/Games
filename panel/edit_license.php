<?php
ini_set('display_errors', 1);
error_reporting(E_ALL);

$license_id = filter_input(INPUT_GET, 'id', FILTER_VALIDATE_INT);
if (!$license_id) {
    echo "Geçersiz Lisans ID.";
    exit;
}

$form_err = $form_success = "";

if ($_SERVER["REQUEST_METHOD"] == "POST") {
    // Hangi butona basıldığını kontrol et
    if (isset($_POST['action']) && $_POST['action'] == 'reset_hwid') {
        // Sadece HWID sıfırlama işlemi
        $sql = "UPDATE licenses SET hwid = NULL, status = 'pending' WHERE id = ?";
        if ($stmt = $mysqli->prepare($sql)) {
            $stmt->bind_param("i", $license_id);
            if ($stmt->execute()) {
                $form_success = "HWID başarıyla sıfırlandı. Lisans yeniden aktive edilebilir.";
            } else {
                $form_err = "HWID sıfırlanırken bir hata oluştu: " . $stmt->error;
            }
            $stmt->close();
        }
    } else {
        // Normal güncelleme işlemi
        $status = $_POST['status'];
        $end_date = $_POST['end_date'];

        if (empty($end_date)) {
            $form_err = "Bitiş tarihi boş bırakılamaz.";
        } else {
            $sql = "UPDATE licenses SET status = ?, end_date = ? WHERE id = ?";
            if ($stmt = $mysqli->prepare($sql)) {
                $stmt->bind_param("ssi", $status, $end_date, $license_id);
                if ($stmt->execute()) {
                    $form_success = "Lisans başarıyla güncellendi.";
                } else {
                    $form_err = "Güncelleme sırasında bir hata oluştu: " . $stmt->error;
                }
                $stmt->close();
            }
        }
    }
}

// Mevcut lisans bilgilerini her zaman yeniden çek
$license = null;
$sql_select = "SELECT l.*, c.name as customer_name FROM licenses l JOIN customers c ON l.customer_id = c.id WHERE l.id = ?";
if ($stmt_select = $mysqli->prepare($sql_select)) {
    $stmt_select->bind_param("i", $license_id);
    if ($stmt_select->execute()) {
        $result = $stmt_select->get_result();
        if ($result->num_rows == 1) {
            $license = $result->fetch_assoc();
        } else { exit; }
    }
    $stmt_select->close();
}
?>

<div>
    <h3 class="text-xl font-bold mb-6 text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600">
        Lisans Düzenle: <?php echo htmlspecialchars($license['customer_name']); ?>
    </h3>
    
    <?php 
    if(!empty($form_err)) echo '<div class="bg-red-500/10 text-red-400 border border-red-500/20 p-3 rounded-lg mb-4 text-sm">' . $form_err . '</div>';
    if(!empty($form_success)) echo '<div class="bg-green-500/10 text-green-400 border border-green-500/20 p-3 rounded-lg mb-4 text-sm">' . $form_success . '</div>';
    ?>

    <form action="index.php?tab=edit_license&id=<?php echo $license_id; ?>" method="post">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Lisans Anahtarı</label>
                <input type="text" readonly value="<?php echo htmlspecialchars($license['license_key']); ?>" class="w-full px-4 py-2.5 bg-slate-900/70 border border-slate-700 rounded-lg text-slate-400" />
            </div>
             <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Bitiş Tarihi (*)</label>
                <input type="date" name="end_date" value="<?php echo htmlspecialchars($license['end_date']); ?>" required class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Lisans Durumu</label>
                <select name="status" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition">
                    <option value="active" <?php echo ($license['status'] == 'active') ? 'selected' : ''; ?>>Aktif</option>
                    <option value="pending" <?php echo ($license['status'] == 'pending') ? 'selected' : ''; ?>>Beklemede</option>
                    <option value="expired" <?php echo ($license['status'] == 'expired') ? 'selected' : ''; ?>>Süresi Doldu</option>
                    <option value="cancelled" <?php echo ($license['status'] == 'cancelled') ? 'selected' : ''; ?>>İptal Edildi</option>
                </select>
            </div>
             <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Donanım ID (HWID)</label>
                <input type="text" readonly name="hwid" value="<?php echo htmlspecialchars($license['hwid'] ?? 'Henüz atanmamış'); ?>" class="w-full px-4 py-2.5 bg-slate-900/70 border border-slate-700 rounded-lg text-slate-400" />
            </div>
            <div class="md:col-span-2 flex items-center space-x-4">
                <button type="submit" name="action" value="update" class="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg font-semibold hover:from-blue-600 hover:to-purple-700 transition transform hover:scale-[1.02] shadow-lg">
                    Lisansı Güncelle
                </button>
                <button type="submit" name="action" value="reset_hwid" class="px-6 py-3 bg-orange-500/20 text-orange-400 border border-orange-500/30 rounded-lg font-semibold hover:bg-orange-500/30 transition" onclick="return confirm('Bu lisansın donanım kaydını sıfırlamak istediğinizden emin misiniz?');">
                    HWID Sıfırla
                </button>
                <a href="index.php?tab=customers" class="px-6 py-3 bg-slate-700/50 rounded-lg font-semibold hover:bg-slate-600/50 transition">Geri</a>
            </div>
        </div>
    </form>
</div>