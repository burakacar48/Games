<?php
// Gerekli başlıkları ayarla (JSON yanıtı için)
header("Content-Type: application/json; charset=UTF-8");

// Veritabanı yapılandırmasını dahil et
require_once "config.php";

// Yanıt için bir dizi oluştur
$response = ['status' => 'invalid', 'reason' => 'Bilinmeyen bir hata oluştu.'];
$debug_info = []; // DEBUG BİLGİSİ İÇİN YENİ DİZİ
$license_details = null; // LİSANS DETAYLARI İÇİN YENİ BLOK

// Gelen isteğin POST olduğundan emin ol
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    
    // Gelen JSON verisini al ve PHP dizisine çevir
    $input = json_decode(file_get_contents('php://input'), true);

    // Gelen tüm kritik değerleri temizle
    $license_key = trim((string)($input['license_key'] ?? ''));
    $hwid = trim((string)($input['hwid'] ?? '')); 
    $client_ip = trim((string)($input['client_ip'] ?? '')); 

    // DEBUG BİLGİSİNİ DOLDUR
    $debug_info['client_ip_incoming'] = $client_ip;
    $debug_info['hwid_incoming'] = $hwid;
    $debug_info['license_key'] = $license_key;

    // KRİTİK GÜVENLİK KONTROLÜ: Gelen HWID boşsa reddet
    if (empty($hwid)) {
        $response['reason'] = '( Donanım Kimliği Eksik )'; 
    } elseif (empty($license_key)) {
        $response['reason'] = '( Lisans Anahtarı Eksik )'; 
    } else {
        // Lisans anahtarını ve müşteri bilgilerini veritabanında ara
        // YENİ SORGUSU: Tüm müşteri ve lisans detayları çekiliyor.
        $sql = "SELECT l.*, l.start_date, l.end_date, c.name, c.company, c.address, c.city, c.district
                FROM licenses l 
                JOIN customers c ON l.customer_id = c.id 
                WHERE l.license_key = ?";
        
        if ($stmt = $mysqli->prepare($sql)) {
            $stmt->bind_param("s", $license_key);
            
            if ($stmt->execute()) {
                $result = $stmt->get_result();
                
                if ($result->num_rows == 1) {
                    $license = $result->fetch_assoc();
                    
                    // DB'den gelen kritik değerleri temizle
                    $licensed_ip = trim((string)($license['licensed_ip'] ?? '')); 
                    $hwid_db = trim((string)($license['hwid'] ?? '')); 
                    
                    $debug_info['hwid_db'] = $hwid_db;
                    $debug_info['licensed_ip_db'] = $licensed_ip;

                    // LİSANS DETAYLARINI DOLDUR (Ekran gösterimi için formatlanmış)
                    $license_details = [
                        'customer_name' => $license['name'],
                        'company' => $license['company'],
                        'address_details' => trim($license['address'] . ' ' . $license['city'] . '/' . $license['district']),
                        'start_date' => date("d.m.Y H:i", strtotime($license['start_date'])),
                        'end_date' => date("d.m.Y H:i", strtotime($license['end_date'])),
                    ];


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
                    elseif (empty($hwid_db)) {
                        
                        // YENİ KURAL: IP adresi PANEL'de ayarlanmış olmalı!
                        if (empty($licensed_ip)) {
                            // Hata: HWID geldi ama IP ayarlanmamış
                            $response['reason'] = '( IP Adresi Doğrulanmadı )'; 
                            $debug_info['activation_status'] = 'IP DBde BOS';
                        } else {
                            // Katı eşleşme: SADECE gelen IP, kayıtlı IP ile EŞLEŞMELİ.
                            if ($licensed_ip === $client_ip) {
                                // Aktivasyon Kuralları Karşılandı: HWID kaydı yapılıyor
                                $update_sql = "UPDATE licenses SET hwid = ?, status = 'active' WHERE id = ?";
                                if($update_stmt = $mysqli->prepare($update_sql)) {
                                    $update_stmt->bind_param("si", $hwid, $license['id']);
                                    if($update_stmt->execute()){
                                        $response = ['status' => 'valid', 'message' => 'Lisans başarıyla bu cihaza atandı ve IP adresi doğrulandı.'];
                                        $debug_info['activation_status'] = 'HWID Kaydedildi ve IP Eşleşti';
                                    } else {
                                        $response['reason'] = '( Veritabanı Hatası )';
                                        $debug_info['activation_status'] = 'DB Hatası';
                                    }
                                    $update_stmt->close();
                                }
                            } else {
                                $response['reason'] = '( IP Adresi Eşleşmiyor )';
                                $debug_info['activation_status'] = 'IP Eşleşmedi';
                            }
                        }
                    }
                    // 2. SONRAKİ KONTROL: DB'de HWID dolu.
                    elseif ($hwid_db === $hwid) {
                        // HWID (Anakart Seri No) eşleşti. Şimdi IP kontrolü.
                        
                        if (empty($licensed_ip)) {
                            // Hata: HWID eşleşti ama IP ayarlanmamış
                            $response['reason'] = '( IP Adresi Doğrulanmadı )'; 
                            $debug_info['validation_step'] = 'IP DBde BOS';
                        }
                        // HWID ve IP adreslerinin ikisi de eşleşmeli
                        elseif ($licensed_ip === $client_ip) {
                            $response = ['status' => 'valid', 'message' => 'Lisans doğrulandı.'];
                            $debug_info['validation_step'] = 'HWID ve IP Eşleşti';
                        } else {
                            $response['reason'] = '( IP Adresi Eşleşmiyor )';
                            $debug_info['validation_step'] = 'HWID Eşleşti, IP Eşleşmedi';
                        }
                    }
                    // 3. HWID eşleşmiyorsa
                    else {
                        $response['reason'] = '( Farklı Cihaza Kayıtlı )';
                        $debug_info['validation_step'] = 'HWID Eşleşmedi';
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

// YANITA DEBUG BİLGİSİNİ EKLE
if ($debug_info) {
    $response['debug'] = $debug_info;
}
// YENİ: LİSANS DETAYLARINI EKLE
if ($license_details) {
    $response['license_details'] = $license_details;
}

// Sonucu JSON formatında ekrana yazdır
echo json_encode($response, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
?>