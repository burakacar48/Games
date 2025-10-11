<?php
// Müşteri ve lisans bilgilerini birleştirerek çek
$sql = "SELECT c.id as customer_id, c.name, l.license_type, l.start_date, l.end_date, l.status, l.id as license_id
        FROM customers c
        JOIN licenses l ON c.id = l.customer_id
        ORDER BY c.name ASC";
$result = $mysqli->query($sql);

function getStatusBadge($status) { 
    switch ($status) {
        case 'active':
            return '<span class="px-3 py-1 text-sm font-semibold rounded-full bg-green-500/20 text-green-400">Aktif</span>';
        case 'pending':
            return '<span class="px-3 py-1 text-sm font-semibold rounded-full bg-yellow-500/20 text-yellow-400">Beklemede</span>';
        case 'expired':
            return '<span class="px-3 py-1 text-sm font-semibold rounded-full bg-red-500/20 text-red-400">Süresi Doldu</span>';
        case 'cancelled':
            return '<span class="px-3 py-1 text-sm font-semibold rounded-full bg-slate-500/20 text-slate-400">İptal Edildi</span>';
        default:
            return '<span class="px-3 py-1 text-sm font-semibold rounded-full bg-slate-500/20 text-slate-400">Bilinmiyor</span>';
    }
}
?>
<div>
    <div class="flex items-center justify-between mb-6 flex-wrap gap-4">
        <div class="relative flex-1 max-w-md"><i data-lucide="search" class="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-400"></i><input type="text" placeholder="Müşteri ara..." class="w-full pl-10 pr-4 py-2.5 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition" /></div>
        <a href="?tab=add_customer" class="flex items-center space-x-2 px-4 py-2.5 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg font-semibold hover:from-blue-600 hover:to-purple-700 transition transform hover:scale-[1.02] shadow-lg"><i data-lucide="plus" class="w-4 h-4"></i><span>Yeni Müşteri</span></a>
    </div>
    <div class="overflow-x-auto">
        <table class="w-full">
            <thead>
                <tr class="border-b border-slate-700">
                    <th class="text-left py-4 px-4 text-slate-400 font-semibold text-sm">MÜŞTERİ ADI</th>
                    <th class="text-left py-4 px-4 text-slate-400 font-semibold text-sm">LİSANS TİPİ</th>
                    <th class="text-left py-4 px-4 text-slate-400 font-semibold text-sm">BİTİŞ</th>
                    <th class="text-left py-4 px-4 text-slate-400 font-semibold text-sm">DURUM</th>
                    <th class="text-left py-4 px-4 text-slate-400 font-semibold text-sm">İŞLEMLER</th>
                </tr>
            </thead>
            <tbody>
                <?php if ($result && $result->num_rows > 0): ?>
                    <?php while($row = $result->fetch_assoc()): ?>
                        <tr class="border-b border-slate-700/50 hover:bg-slate-700/20 transition">
                            <td class="py-4 px-4 font-medium"><?php echo htmlspecialchars($row['name']); ?></td>
                            <td class="py-4 px-4 text-slate-300"><?php echo htmlspecialchars($row['license_type']); ?></td>
                            <td class="py-4 px-4 text-slate-400"><?php echo date("d.m.Y", strtotime($row['end_date'])); ?></td>
                            <td class="py-4 px-4"><?php echo getStatusBadge($row['status']); ?></td>
                            <td class="py-4 px-4">
                                <div class="flex space-x-2">
                                    <a href="index.php?tab=edit_license&id=<?php echo $row['license_id']; ?>" title="Lisansı ve Müşteriyi Düzenle" class="p-2 bg-blue-500/10 text-blue-400 rounded-lg hover:bg-blue-500/20 transition"><i data-lucide="key-round" class="w-4 h-4"></i></a>
                                    <a href="delete_license.php?id=<?php echo $row['license_id']; ?>" title="Sil" class="p-2 bg-red-500/10 text-red-400 rounded-lg hover:bg-red-500/20 transition" onclick="return confirm('Bu lisansı ve potansiyel olarak müşteri kaydını kalıcı olarak silmek istediğinizden emin misiniz?');"><i data-lucide="trash-2" class="w-4 h-4"></i></a>
                                </div>
                            </td>
                        </tr>
                    <?php endwhile; ?>
                <?php else: ?>
                    <tr><td colspan="5" class="text-center py-8 text-slate-500">Henüz müşteri veya lisans kaydı bulunmuyor.</td></tr>
                <?php endif; ?>
            </tbody>
        </table>
    </div>
</div>