<?php
require_once "config.php";
// Oturum kontrolü
if(!isset($_SESSION["loggedin"]) || $_SESSION["loggedin"] !== true){
    header("location: login.php");
    exit;
}

// Silinecek lisansın ID'sini al
$license_id = filter_input(INPUT_GET, 'id', FILTER_VALIDATE_INT);
if (!$license_id) {
    // Geçersiz ID ise ana sayfaya yönlendir
    header("location: index.php?tab=customers");
    exit;
}

$customer_id = null;
$customer_license_count = 0;

// Önce lisansa ait müşteri ID'sini ve o müşterinin toplam lisans sayısını bul
$sql_check = "SELECT customer_id, (SELECT COUNT(*) FROM licenses WHERE customer_id = l.customer_id) as license_count FROM licenses l WHERE id = ?";
if($stmt_check = $mysqli->prepare($sql_check)){
    $stmt_check->bind_param("i", $license_id);
    $stmt_check->execute();
    $result_check = $stmt_check->get_result();
    if($row = $result_check->fetch_assoc()){
        $customer_id = $row['customer_id'];
        $customer_license_count = $row['license_count'];
    }
    $stmt_check->close();
}

// Şimdi silme işlemine geç
if($customer_id){
    // 1. Lisansı sil
    $sql_delete_license = "DELETE FROM licenses WHERE id = ?";
    if($stmt_delete_license = $mysqli->prepare($sql_delete_license)){
        $stmt_delete_license->bind_param("i", $license_id);
        $stmt_delete_license->execute();
        $stmt_delete_license->close();
    }

    // 2. Eğer bu müşterinin tek lisansı buysa, müşteriyi ve ödemelerini de sil
    if($customer_license_count == 1){
        // Önce ödemeleri sil
        $sql_delete_payments = "DELETE FROM payments WHERE customer_id = ?";
        if($stmt_delete_payments = $mysqli->prepare($sql_delete_payments)){
            $stmt_delete_payments->bind_param("i", $customer_id);
            $stmt_delete_payments->execute();
            $stmt_delete_payments->close();
        }

        // Sonra müşteriyi sil
        $sql_delete_customer = "DELETE FROM customers WHERE id = ?";
        if($stmt_delete_customer = $mysqli->prepare($sql_delete_customer)){
            $stmt_delete_customer->bind_param("i", $customer_id);
            $stmt_delete_customer->execute();
            $stmt_delete_customer->close();
        }
    }
}

// İşlem bittikten sonra müşteri listesine geri dön
header("location: index.php?tab=customers");
exit;
?>