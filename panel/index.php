<?php
require_once "header.php";
$total_customers_result = $mysqli->query("SELECT COUNT(id) as count FROM customers");
$total_customers = $total_customers_result->fetch_assoc()['count'];
$active_licenses_result = $mysqli->query("SELECT COUNT(id) as count FROM licenses WHERE status = 'active'");
$active_licenses = $active_licenses_result->fetch_assoc()['count'];
$expired_licenses_result = $mysqli->query("SELECT COUNT(id) as count FROM licenses WHERE status = 'expired' OR end_date < CURDATE()");
$expired_licenses = $expired_licenses_result->fetch_assoc()['count'];
$monthly_revenue = "0.00";
$activeTab = $_GET['tab'] ?? 'customers';
?>
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
    <div class="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-6 shadow-xl"><div class="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center mb-4"><i data-lucide="users" class="w-6 h-6"></i></div><p class="text-slate-400 text-xs font-semibold mb-1">TOPLAM MÜŞTERİ</p><p class="text-3xl font-bold mb-1"><?php echo $total_customers; ?></p></div>
    <div class="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-6 shadow-xl"><div class="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center mb-4"><i data-lucide="package" class="w-6 h-6"></i></div><p class="text-slate-400 text-xs font-semibold mb-1">AKTİF LİSANS</p><p class="text-3xl font-bold mb-1"><?php echo $active_licenses; ?></p></div>
    <div class="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-6 shadow-xl"><div class="w-12 h-12 rounded-xl bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center mb-4"><i data-lucide="alert-circle" class="w-6 h-6"></i></div><p class="text-slate-400 text-xs font-semibold mb-1">SÜRESİ DOLAN</p><p class="text-3xl font-bold mb-1"><?php echo $expired_licenses; ?></p></div>
    <div class="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-6 shadow-xl"><div class="w-12 h-12 rounded-xl bg-gradient-to-br from-green-500 to-green-600 flex items-center justify-center mb-4"><i data-lucide="trending-up" class="w-6 h-6"></i></div><p class="text-slate-400 text-xs font-semibold mb-1">AYLIK GELİR</p><p class="text-3xl font-bold mb-1">₺<?php echo $monthly_revenue; ?></p></div>
</div>
<div class="flex space-x-2 mb-6 overflow-x-auto pb-2">
    <?php
    $tabs = ['customers' => ['label' => 'Müşteriler', 'icon' => 'users'], 'dealers' => ['label' => 'Bayiler', 'icon' => 'building-2'], 'add_customer' => ['label' => 'Müşteri Ekle', 'icon' => 'plus'], 'payments' => ['label' => 'Ödemeler', 'icon' => 'credit-card']];
    foreach ($tabs as $tabId => $tab) {
        $isActive = ($activeTab === $tabId);
        $activeClass = $isActive ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg' : 'bg-slate-800/50 text-slate-400 hover:text-white border border-slate-700/50';
        echo '<a href="?tab=' . $tabId . '" class="flex items-center space-x-2 px-4 py-2.5 rounded-lg font-medium transition whitespace-nowrap ' . $activeClass . '"><i data-lucide="' . $tab['icon'] . '" class="w-4 h-4"></i><span>' . $tab['label'] . '</span></a>';
    }
    ?>
</div>
<div class="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-6 shadow-xl">
    <?php
    if ($activeTab === 'customers') { include 'customers.php'; } 
    elseif ($activeTab === 'dealers') { echo "<p>Bayiler bölümü yapım aşamasında.</p>"; } 
    elseif ($activeTab === 'add_customer') { include 'add_customer.php'; } 
    elseif ($activeTab === 'edit_license') { include 'edit_license.php'; } 
    elseif ($activeTab === 'edit_customer') { include 'edit_customer.php'; } // YENİ EKLENDİ
    elseif ($activeTab === 'payments') { echo "<p>Ödemeler bölümü yapım aşamasında.</p>"; }
    ?>
</div>
<?php require_once "footer.php"; ?>