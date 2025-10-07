import sqlite3
from werkzeug.security import generate_password_hash

def init_db():
    print("Veritabanı kontrol ediliyor ve eksik tablolar oluşturuluyor...")
    try:
        conn = sqlite3.connect('kafe.db')
        cursor = conn.cursor()

        # MEVCUT VERİLERİ SİLEN 'DROP TABLE' KOMUTLARI TAMAMEN KALDIRILDI.
        # Artık sadece tablo yoksa oluşturulacak.

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            oyun_adi TEXT NOT NULL,
            aciklama TEXT,
            cover_image TEXT,
            youtube_id TEXT,
            save_yolu TEXT,
            calistirma_tipi TEXT NOT NULL,
            calistirma_verisi TEXT NOT NULL,
            cikis_yili TEXT,
            pegi TEXT,
            category_id INTEGER,
            average_rating REAL NOT NULL DEFAULT 0,
            rating_count INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_ratings (
            user_id INTEGER NOT NULL,
            game_id INTEGER NOT NULL,
            rating REAL NOT NULL,
            PRIMARY KEY (user_id, game_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (game_id) REFERENCES games(id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_favorites (
            user_id INTEGER NOT NULL,
            game_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, game_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (game_id) REFERENCES games(id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS gallery_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            game_id INTEGER NOT NULL, 
            image_path TEXT NOT NULL,
            FOREIGN KEY (game_id) REFERENCES games (id)
        )
        ''')
        
        # Örnek veri ekleme blokları, sadece ilgili tablo boşsa çalışır.
        # Bu sayede mevcut kullanıcıların ve oyunların üzerine veri yazılmaz.
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            password_hash = generate_password_hash('12345')
            cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', ('testuser', password_hash))
            print("Tablo boştu, örnek kullanıcı eklendi.")

        cursor.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] == 0:
            print("Tablo boştu, örnek kategoriler ekleniyor...")
            sample_categories = [('FPS',), ('RPG',), ('MOBA',), ('Strateji',)]
            cursor.executemany('INSERT INTO categories (name) VALUES (?)', sample_categories)

        cursor.execute("SELECT COUNT(*) FROM games")
        if cursor.fetchone()[0] == 0:
            print("Tablo boştu, örnek oyun verileri ekleniyor...")
            sample_games = [
                ('Valorant', '5v5 karakter tabanlı taktiksel nişancı oyunu.', 'valorant.jpg', 'e_E9W2vsRbI', '%LOCALAPPDATA%\\ShooterGame\\Saved\\', 'exe', '{"yol": "C:\\Riot Games\\Riot Client\\RiotClientServices.exe", "argumanlar": "--launch-product=valorant --launch-patchline=live"}', '2020', 'PEGI 16', 1),
                ('Counter-Strike 2', 'CS tarihinde yeni bir dönem başlıyor. Karşınızda Counter-Strike 2.', 'cs2.png', 'vjS2y_x-WUc', '%USERPROFILE%\\Documents\\KafeTestSaves\\CS2', 'steam', '{"app_id": "730"}', '2023', 'PEGI 18', 1)
            ]
            cursor.executemany('INSERT INTO games (oyun_adi, aciklama, cover_image, youtube_id, save_yolu, calistirma_tipi, calistirma_verisi, cikis_yili, pegi, category_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', sample_games)
            
            print("Örnek galeri görselleri ekleniyor...")
            cursor.execute("INSERT INTO gallery_images (game_id, image_path) VALUES (?, ?)", (1, 'valorant_ss1.jpg'))
            cursor.execute("INSERT INTO gallery_images (game_id, image_path) VALUES (?, ?)", (2, 'cs2_ss1.jpg'))

        conn.commit()
        conn.close()
        print("Veritabanı kontrolü tamamlandı. Mevcut veriler korundu.")
    except Exception as e:
        print(f"Bir hata oluştu: {e}")

if __name__ == '__main__':
    init_db()