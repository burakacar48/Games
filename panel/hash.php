<?php
// Hata raporlamayı aç
ini_set('display_errors', 1);
error_reporting(E_ALL);

// Değiştirmek istediğiniz şifre
$sifre = 'admin123';

// Şifreyi hash'le
$hash = password_hash($sifre, PASSWORD_DEFAULT);

// Ekrana sadece hash'i yazdır
echo "Yeni Şifre Hash'iniz:<br><br>";
echo "<textarea style='width:100%; height: 80px; font-family: monospace;'>" . htmlspecialchars($hash) . "</textarea>";
?>