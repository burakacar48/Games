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
    $client_ip = $input['client_ip'] ?? ''; 

    // KRİTİK GÜVENLİK KONTROLÜ: Gelen HWID boşsa reddet
    if (empty($hwid)) {
        $response['reason'] = '( Donanım Kimliği Eksik )'; // Kısa HWID eksik mesajı
    } elseif (empty($license_key)) {
        $response['reason'] = '( Lisans Anahtarı Eksik )'; // Kısa Lisans eksik mesajı
    } else {
        // Lisans anahtarını veritabanında ara (licensed_ip kolonunu çekiyoruz)
        $sql = "SELECT id, customer_id, hwid, licensed_ip, end_date, status FROM licenses WHERE license_key = ?";
        
        if ($stmt = $mysqli->prepare($sql)) {
            $stmt->bind_param("s", $license_key);
            
            if ($stmt->execute()) {
                $result = $stmt->get_result();
                
                if ($result->num_rows == 1) {
                    $license = $result->fetch_assoc();

                    // Lisansın durumunu kontrol et
                    if ($license['status'] === 'cancelled' || $license['status'] === 'expired') {
                        $response['reason'] = '( İptal Edildi veya Süresi Doldu )';
                    } 
                    // Lisansın son kullanım tarihini kontrol et
                    elseif (strtotime($license['end_date']) < time()) {
                        $response['reason'] = '( Süresi Doldu )';
                        $mysqli->query("UPDATE licenses SET status = 'expired' WHERE id = " . $license['id']);
                    }
                    // 1. İLK KONTROL: DB'de HWID boş mu? (Initial Activation)
                    elseif (empty($license['hwid'])) {
                        $licensed_ip = $license['licensed_ip'] ?? '';
                        
                        // YENİ KURAL: IP adresi PANEL'de ayarlanmış olmalı!
                        if (empty($licensed_ip)) {
                            // Hata: HWID geldi ama IP ayarlanmamış
                            $response['reason'] = '( IP Adresi Doğrulanmadı )'; // İstenen Mesaj
                        } else {
                            // IP kısıtlaması var. Şimdi gelen IP'yi kontrol et.
                            if ($licensed_ip === $client_ip) {
                                // Aktivasyon Kuralları Karşılandı: HWID kaydı yapılıyor
                                $update_sql = "UPDATE licenses SET hwid = ?, status = 'active' WHERE id = ?";
                                if($update_stmt = $mysqli->prepare($update_sql)) {
                                    $update_stmt->bind_param("si", $hwid, $license['id']);
                                    if($update_stmt->execute()){
                                        $response = ['status' => 'valid', 'message' => 'Lisans başarıyla bu cihaza atandı ve IP adresi doğrulandı.'];
                                    } else {
                                        $response['reason'] = '( Veritabanı Hatası )';
                                    }
                                    $update_stmt->close();
                                }
                            } else {
                                $response['reason'] = '( IP Adresi Eşleşmiyor )';
                            }
                        }
                    }
                    // 2. SONRAKİ KONTROL: DB'de HWID dolu.
                    elseif ($license['hwid'] === $hwid) {
                        // HWID (Anakart Seri No) eşleşti. Şimdi IP kontrolü.
                        $licensed_ip = $license['licensed_ip'] ?? '';
                        
                        if (empty($licensed_ip)) {
                            // Hata: HWID eşleşti ama IP ayarlanmamış
                            $response['reason'] = '( IP Adresi Doğrulanmadı )'; // İstenen Mesaj
                        }
                        // HWID ve IP adreslerinin ikisi de eşleşmeli
                        elseif ($licensed_ip === $client_ip) {
                            $response = ['status' => 'valid', 'message' => 'Lisans doğrulandı.'];
                        } else {
                            $response['reason'] = '( IP Adresi Eşleşmiyor )';
                        }
                    }
                    // 3. HWID eşleşmiyorsa
                    else {
                        $response['reason'] = '( Farklı Cihaza Kayıtlı )';
                    }

                } else {
                    $response['reason'] = '( Geçersiz Lisans Anahtarı )';
                }
            } else {
                $response['reason'] = '( Veritabanı Sorgu Hatası )';
            }
            $stmt->close();
        }
    }
} else {
    $response['reason'] = 'Geçersiz istek metodu.';
}

$mysqli->close();

// Sonucu JSON formatında ekrana yazdır
echo json_encode($response, JSON_UNESCAPED_UNICODE);
?>