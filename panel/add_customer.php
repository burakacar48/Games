<?php
// Bu dosya, index.php tarafından çağrıldığı için config.php zaten dahil edilmiştir.

$name = $email = $phone = $company = $start_date = $end_date = "";
// YENİ ALANLAR EKLENDİ
$address = $city = $district = "";
$form_err = "";
$form_success = "";

// Form gönderildiğinde çalışacak kod bloğu
if ($_SERVER["REQUEST_METHOD"] == "POST" && isset($_POST['add_customer'])) {

    // Form verilerini al
    $name = trim($_POST['name']);
    $email = trim($_POST['email']);
    $phone = trim($_POST['phone']);
    $company = trim($_POST['company']);
    // YENİ EKLENEN ALANLAR ALINIYOR
    $address = trim($_POST['address']);
    $city = trim($_POST['city']);
    $district = trim($_POST['district']);
    
    $start_date = $_POST['start_date'];
    $end_date = $_POST['end_date'];
    
    // Lisans tipini varsayılan olarak "Standard" ayarla
    $license_type = 'Standard';

    // Basit doğrulama
    if (empty($name) || empty($start_date) || empty($end_date)) {
        $form_err = "Lütfen tüm zorunlu alanları doldurun (Müşteri Adı, Tarihler).";
    } else {
        
        // 1. Müşteriyi veritabanına ekle
        // SORGUNUN GÜNCELLENMESİ: 7 parametre eklendi
        $sql_customer = "INSERT INTO customers (name, email, phone, company, address, city, district) VALUES (?, ?, ?, ?, ?, ?, ?)";
        
        if ($stmt_customer = $mysqli->prepare($sql_customer)) {
            // BAĞLAMANIN GÜNCELLENMESİ: sssssss (name, email, phone, company, address, city, district)
            $stmt_customer->bind_param("sssssss", $name, $email, $phone, $company, $address, $city, $district);
            
            if ($stmt_customer->execute()) {
                // Başarılı olursa, eklenen müşterinin ID'sini al
                $customer_id = $stmt_customer->insert_id;

                // 2. Benzersiz bir lisans anahtarı oluştur (varsayılan tipe göre)
                $prefix = "KA-STD"; // Standard için sabit prefix
                $license_key = $prefix . "-" . substr(str_shuffle(str_repeat('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', 12)), 0, 4) . "-" . substr(str_shuffle(str_repeat('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', 12)), 0, 4);

                // 3. Lisansı veritabanına ekle
                $sql_license = "INSERT INTO licenses (customer_id, license_key, license_type, start_date, end_date, status) VALUES (?, ?, ?, ?, ?, 'active')";
                
                if ($stmt_license = $mysqli->prepare($sql_license)) {
                    $stmt_license->bind_param("issss", $customer_id, $license_key, $license_type, $start_date, $end_date);
                    
                    if ($stmt_license->execute()) {
                        $form_success = "Müşteri ve lisansı başarıyla oluşturuldu! Müşteriler sekmesine yönlendiriliyorsunuz...";
                        // Başarılı kayıt sonrası 2 saniye sonra yönlendir
                        header("refresh:2;url=index.php?tab=customers");
                    } else {
                        $form_err = "Lisans oluşturulurken bir hata oluştu.";
                    }
                    $stmt_license->close();
                }
            } else {
                $form_err = "Müşteri oluşturulurken bir hata oluştu.";
            }
            $stmt_customer->close();
        }
    }
}
?>

<div>
    <h3 class="text-xl font-bold mb-6 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-600">
        Yeni Müşteri ve Lisans Oluştur
    </h3>

    <?php 
    if(!empty($form_err)){
        echo '<div class="bg-red-500/10 text-red-400 border border-red-500/20 p-3 rounded-lg mb-4 text-sm">' . $form_err . '</div>';
    }
    if(!empty($form_success)){
        echo '<div class="bg-green-500/10 text-green-400 border border-green-500/20 p-3 rounded-lg mb-4 text-sm">' . $form_success . '</div>';
    }
    ?>

    <form action="index.php?tab=add_customer" method="post">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Müşteri Adı (*)</label>
                <input type="text" name="name" placeholder="Ad Soyad" required class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Email</label>
                <input type="email" name="email" placeholder="email@example.com" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Telefon</label>
                <input type="tel" name="phone" placeholder="0XXX XXX XX XX" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Şirket / Kafe Adı</label>
                <input type="text" name="company" placeholder="Kafe Adı" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">İl</label>
                <input type="text" name="city" placeholder="Şehir Adı" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">İlçe</label>
                <input type="text" name="district" placeholder="İlçe Adı" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            <div class="md:col-span-2">
                <label class="block text-sm font-medium text-slate-300 mb-2">Adres</label>
                <textarea name="address" rows="3" placeholder="Açık Adres Bilgisi" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"></textarea>
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Başlangıç Tarihi (*)</label>
                <input type="date" name="start_date" required class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
            <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Bitiş Tarihi (*)</label>
                <input type="date" name="end_date" required class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" />
            </div>
             <div class="md:col-span-2">
                <label class="block text-sm font-medium text-slate-300 mb-2">Bayi</label>
                <select name="dealer_id" class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition">
                    <option value="">Bayi Yok</option>
                    </select>
            </div>
            <div class="md:col-span-2">
                <button type="submit" name="add_customer" class="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg font-semibold hover:from-blue-600 hover:to-purple-700 transition transform hover:scale-[1.02] shadow-lg">
                    Müşteri ve Lisans Oluştur
                </button>
            </div>
        </div>
    </form>
</div>