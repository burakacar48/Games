<?php
// Hata raporlamayı aç
ini_set('display_errors', 1);
error_reporting(E_ALL);

// Müşteri ID'sini al
$customer_id = filter_input(INPUT_GET, 'id', FILTER_VALIDATE_INT);
if (!$customer_id) {
    echo "Geçersiz Müşteri ID.";
    exit;
}

$form_err = $form_success = "";

// Form gönderildiğinde
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $name = trim($_POST['name']);
    $email = trim($_POST['email']);
    $phone = trim($_POST['phone']);
    $company = trim($_POST['company']);
    // YENİ EKLENEN ALANLAR ALINIYOR
    $address = trim($_POST['address']);
    $city = trim($_POST['city']);
    $district = trim($_POST['district']);
    // YENİ EKLENEN ALANLAR SONU

    if (empty($name)) {
        $form_err = "Müşteri adı boş bırakılamaz.";
    } else {
        // SORGUNUN GÜNCELLENMESİ: address, city, district eklendi
        $sql = "UPDATE customers SET name = ?, email = ?, phone = ?, company = ?, address = ?, city = ?, district = ? WHERE id = ?";
        if ($stmt = $mysqli->prepare($sql)) {
            // BAĞLAMANIN GÜNCELLENMESİ: sssssssi
            $stmt->bind_param("sssssssi", $name, $email, $phone, $company, $address, $city, $district, $customer_id);
            if ($stmt->execute()) {
                $form_success = "Müşteri bilgileri başarıyla güncellendi. Yönlendiriliyorsunuz...";
                echo "<meta http-equiv='refresh' content='2;url=index.php?tab=customers'>";
            } else {
                $form_err = "Güncelleme sırasında bir hata oluştu: " . $stmt->error;
            }
            $stmt->close();
        }
    }
}

// Mevcut müşteri bilgilerini çek
// SELECT * from customers zaten tüm sütunları çeker.
$customer = null;
$sql_select = "SELECT * FROM customers WHERE id = ?";
if ($stmt_select = $mysqli->prepare($sql_select)) {
    $stmt_select->bind_param("i", $customer_id);
    if ($stmt_select->execute()) {
        $result = $stmt_select->get_result();
        if ($result->num_rows == 1) {
            $customer = $result->fetch_assoc();
        } else {
            echo "Müşteri bulunamadı.";
            exit;
        }
    }
    $stmt_select->close();
}
?>

<div>
    <h3 class="text-xl font-bold mb-6 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-600">
        Müşteri Düzenle: <?php echo htmlspecialchars($customer['name']); ?>
    </h3>
    
    <?php 
    if(!empty($form_err)) echo '<div class="bg-red-500/10 text-red-400 border border-red-500/20 p-3 rounded-lg mb-4 text-sm">' . $form_err . '</div>';
    if(!empty($form_success)) echo '<div class="bg-green-500/10 text-green-400 border border-green-500/20 p-3 rounded-lg mb-4 text-sm">' . $form_success . '</div>';
    ?>

    <form action="index.php?tab=edit_customer&id=<?php echo $customer_id; ?>" method="post">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Müşteri Adı (*)</label>
                <input type="text" name="name" value="<?php echo htmlspecialchars($customer['name'] ?? ''); ?>" required class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Email</label>
                <input type="email" name="email" value="<?php echo htmlspecialchars($customer['email'] ?? ''); ?>" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Telefon</label>
                <input type="tel" name="phone" value="<?php echo htmlspecialchars($customer['phone'] ?? ''); ?>" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Şirket / Kafe Adı</label>
                <input type="text" name="company" value="<?php echo htmlspecialchars($customer['company'] ?? ''); ?>" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
             <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">İl</label>
                <input type="text" name="city" value="<?php echo htmlspecialchars($customer['city'] ?? ''); ?>" placeholder="Şehir Adı" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">İlçe</label>
                <input type="text" name="district" value="<?php echo htmlspecialchars($customer['district'] ?? ''); ?>" placeholder="İlçe Adı" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            <div class="md:col-span-2">
                <label class="block text-sm font-medium text-slate-300 mb-2">Adres</label>
                <textarea name="address" rows="3" placeholder="Açık Adres Bilgisi" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"><?php echo htmlspecialchars($customer['address'] ?? ''); ?></textarea>
            </div>
            <div class="md:col-span-2">
                <button type="submit" class="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg font-semibold hover:from-blue-600 hover:to-purple-700 transition transform hover:scale-[1.02] shadow-lg">
                    Bilgileri Güncelle
                </button>
                <a href="index.php?tab=customers" class="ml-4 px-6 py-3 bg-slate-700/50 rounded-lg font-semibold hover:bg-slate-600/50 transition">İptal</a>
            </div>
        </div>
    </form>
</div>