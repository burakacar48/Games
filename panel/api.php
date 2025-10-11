<?php
// Gerekli başlıkları ayarla (JSON yanıtı için)
header("Content-Type: application/json; charset=UTF-8");

// Veritabanı yapılandırmasını dahil et
require_once "config.php";

// Yanıt için bir dizi oluştur
$response = ['status' => 'invalid', 'reason' => 'Bilinmeyen bir hata oluştu.'];

// Gelen isteğin POST olduğundan emin ol
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    
    // Gelen JSON verisini al ve PHP dizisine çevir
    $input = json_decode(file_get_contents('php://input'), true);

    $license_key = $input['license_key'] ?? '';
    $hwid = $input['hwid'] ?? '';

    if (empty($license_key) || empty($hwid)) {
        $response['reason'] = 'Lisans anahtarı veya donanım kimliği eksik.';
    } else {
        // Lisans anahtarını veritabanında ara
        $sql = "SELECT id, customer_id, hwid, end_date, status FROM licenses WHERE license_key = ?";
        
        if ($stmt = $mysqli->prepare($sql)) {
            $stmt->bind_param("s", $license_key);
            
            if ($stmt->execute()) {
                $result = $stmt->get_result();
                
                if ($result->num_rows == 1) {
                    $license = $result->fetch_assoc();

                    // Lisansın durumunu kontrol et
                    if ($license['status'] === 'cancelled' || $license['status'] === 'expired') {
                        $response['reason'] = 'Lisans iptal edilmiş veya süresi dolmuş.';
                    } 
                    // Lisansın son kullanım tarihini kontrol et
                    elseif (strtotime($license['end_date']) < time()) {
                        $response['reason'] = 'Lisansın kullanım süresi dolmuş.';
                        // Durumu veritabanında da güncelle
                        $mysqli->query("UPDATE licenses SET status = 'expired' WHERE id = " . $license['id']);
                    }
                    // İlk aktivasyon mu? (HWID boş ise)
                    elseif (empty($license['hwid'])) {
                        // HWID'yi veritabanına kaydet ve lisansı aktifleştir
                        $update_sql = "UPDATE licenses SET hwid = ?, status = 'active' WHERE id = ?";
                        if($update_stmt = $mysqli->prepare($update_sql)) {
                            $update_stmt->bind_param("si", $hwid, $license['id']);
                            if($update_stmt->execute()){
                                $response = ['status' => 'valid', 'message' => 'Lisans başarıyla bu cihaza atandı.'];
                            } else {
                                $response['reason'] = 'Lisans aktifleştirilirken veritabanı hatası oluştu.';
                            }
                            $update_stmt->close();
                        }
                    }
                    // Sonraki doğrulamalar (HWID eşleşiyor mu?)
                    elseif ($license['hwid'] === $hwid) {
                        $response = ['status' => 'valid', 'message' => 'Lisans doğrulandı.'];
                    }
                    // HWID eşleşmiyorsa
                    else {
                        $response['reason'] = 'Bu lisans anahtarı başka bir cihaza kayıtlıdır.';
                    }

                } else {
                    $response['reason'] = 'Geçersiz lisans anahtarı.';
                }
            } else {
                $response['reason'] = 'Veritabanı sorgusu başarısız oldu.';
            }
            $stmt->close();
        }
    }
} else {
    $response['reason'] = 'Geçersiz istek metodu. Sadece POST istekleri kabul edilir.';
}

$mysqli->close();

// Sonucu JSON formatında ekrana yazdır
echo json_encode($response, JSON_UNESCAPED_UNICODE);
?>