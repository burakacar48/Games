<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

session_start();

define('DB_SERVER', 'localhost');
define('DB_USERNAME', 'oyunmenu');
define('DB_PASSWORD', '4kIryzkAxZ8SRXcXe4Io');
define('DB_NAME', 'oyunmenu');

$mysqli = new mysqli(DB_SERVER, DB_USERNAME, DB_PASSWORD, DB_NAME);

if($mysqli === false){
    die("HATA: Veritabanı bağlantısı kurulamadı. " . $mysqli->connect_error);
}

$mysqli->set_charset("utf8mb4");
?>