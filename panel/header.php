<?php
// config.php dosyasını dahil et ve oturumu başlat
require_once "config.php";

// Kullanıcının giriş yapıp yapmadığını kontrol et, yapmadıysa login sayfasına yönlendir
if(!isset($_SESSION["loggedin"]) || $_SESSION["loggedin"] !== true){
    header("location: login.php");
    exit;
}
?>
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lisans Yönetim Paneli</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="style.css">
    <script src="https://unpkg.com/lucide@latest"></script>
</head>
<body class="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
    <div class="min-h-screen p-6">
        <div class="max-w-7xl mx-auto">
            <div class="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-6 mb-6 shadow-xl">
                <div class="flex items-center justify-between flex-wrap gap-4">
                    <div class="flex items-center space-x-4">
                        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                            <i data-lucide="package" class="w-6 h-6"></i>
                        </div>
                        <div>
                            <h1 class="text-2xl font-bold">Lisans Yönetim Paneli</h1>
                            <p class="text-slate-400 text-sm">Tüm lisanslarınızı tek yerden yönetin</p>
                        </div>
                    </div>
                    <a href="logout.php" class="flex items-center space-x-2 px-4 py-2 bg-red-500/10 text-red-400 rounded-lg hover:bg-red-500/20 border border-red-500/20 transition">
                        <i data-lucide="log-out" class="w-4 h-4"></i>
                        <span>Çıkış</span>
                    </a>
                </div>
            </div>