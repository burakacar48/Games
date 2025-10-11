import sqlite3
from werkzeug.security import generate_password_hash

def init_db():
    print("Veritabanı kontrol ediliyor ve eksik tablolar oluşturuluyor...")
    try:
        conn = sqlite3.connect('kafe.db')
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            icon TEXT
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
            oyun_dili TEXT, 
            average_rating REAL NOT NULL DEFAULT 0,
            rating_count INTEGER NOT NULL DEFAULT 0,
            click_count INTEGER NOT NULL DEFAULT 0,
            launch_script TEXT,
            yuzde_yuz_save_path TEXT
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_categories (
            game_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            PRIMARY KEY (game_id, category_id),
            FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS slider (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER,
            badge_text TEXT,
            title TEXT,
            description TEXT,
            background_image TEXT,
            is_active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            FOREIGN KEY (game_id) REFERENCES games (id)
        )
        ''')
        
        # YENİ: Son oynanan oyunları tutacak tablo
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_played_games (
            user_id INTEGER NOT NULL,
            game_id INTEGER NOT NULL,
            played_at TIMESTAMP NOT NULL,
            PRIMARY KEY (user_id, game_id),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE
        )
        ''')

        try:
            cursor.execute('ALTER TABLE games ADD COLUMN oyun_dili TEXT')
        except: pass
        try:
            cursor.execute('ALTER TABLE games ADD COLUMN click_count INTEGER NOT NULL DEFAULT 0')
        except: pass 
        try:
            cursor.execute('ALTER TABLE games ADD COLUMN launch_script TEXT')
        except: pass
        try:
            cursor.execute('ALTER TABLE games ADD COLUMN yuzde_yuz_save_path TEXT')
        except: pass
        try:
            cursor.execute('ALTER TABLE categories ADD COLUMN icon TEXT')
        except: pass
        try:
            cursor.execute('ALTER TABLE slider ADD COLUMN is_active INTEGER DEFAULT 1')
            cursor.execute('ALTER TABLE slider ADD COLUMN display_order INTEGER DEFAULT 0')
        except: pass

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
        
        if cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            password_hash = generate_password_hash('12345')
            cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', ('testuser', password_hash))

        if cursor.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
            sample_categories = [('FPS', '🎯'), ('RPG', '📜'), ('MOBA', '⚔️'), ('Strateji', '🧠'), ('Online Oyunlar', '🌐')]
            cursor.executemany('INSERT INTO categories (name, icon) VALUES (?, ?)', sample_categories)

        if cursor.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0:
            sample_settings = [
                ('cafe_name', 'Zenka Internet Cafe'), ('slogan', 'Hazırsan, oyun başlasın.'),
                ('background_type', 'default'), ('background_file', ''), ('background_opacity_factor', '1.0'), 
                ('primary_color_start', '#667eea'), ('primary_color_end', '#764ba2'), ('welcome_modal_enabled', '1'),
                ('welcome_modal_text', 'Oyun ilerlemeni kaydetmek, oyunları favorilerine eklemek ve puanlamak için hemen üye girişi yap veya kayıt ol.'),
                ('social_google', 'https://www.google.com'), ('social_instagram', 'https://www.instagram.com'),
                ('social_facebook', 'https://www.facebook.com'), ('social_youtube', 'https://www.youtube.com'),
            ]
            cursor.executemany('INSERT INTO settings (key, value) VALUES (?, ?)', sample_settings)
            
        if cursor.execute("SELECT COUNT(*) FROM games").fetchone()[0] == 0:
            sample_games = [
                ('Valorant', '5v5 karakter tabanlı taktiksel nişancı oyunu.', 'valorant.png', 'e_E9W2vsRbI', '%LOCALAPPDATA%\\ShooterGame\\Saved\\', 'exe', '{"yol": "C:\\Riot Games\\Riot Client\\RiotClientServices.exe", "argumanlar": "--launch-product=valorant --launch-patchline=live"}', '2020', 'PEGI 16', 'İngilizce'),
                ('Counter-Strike 2', 'CS tarihinde yeni bir dönem başlıyor. Karşınızda Counter-Strike 2.', 'CS2.jpg', 'vjS2y_x-WUc', '%USERPROFILE%\\Documents\\KafeTestSaves\\CS2', 'steam', '{"app_id": "730"}', '2023', 'PEGI 18', 'Türkçe Altyazı')
            ]
            cursor.executemany('INSERT INTO games (oyun_adi, aciklama, cover_image, youtube_id, save_yolu, calistirma_tipi, calistirma_verisi, cikis_yili, pegi, oyun_dili) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', sample_games)
            cursor.execute('INSERT INTO game_categories (game_id, category_id) VALUES (1, 1)')
            cursor.execute('INSERT INTO game_categories (game_id, category_id) VALUES (1, 5)')
            cursor.execute('INSERT INTO game_categories (game_id, category_id) VALUES (2, 1)')
            cursor.execute('INSERT INTO game_categories (game_id, category_id) VALUES (2, 5)')
            cursor.execute("INSERT INTO gallery_images (game_id, image_path) VALUES (?, ?)", (1, 'Featured-Image-GE-1.webp'))
            cursor.execute("INSERT INTO gallery_images (game_id, image_path) VALUES (?, ?)", (2, 'Counter-Strike-2-4.jpg'))

        if cursor.execute("SELECT COUNT(*) FROM slider").fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO slider (game_id, badge_text, title, description, background_image) 
                VALUES (?, ?, ?, ?, ?)
            ''', (2, '🔥 POPÜLER', 'Counter-Strike 2', 'CS tarihinde yeni bir dönem başlıyor. Karşınızda Counter-Strike 2.', 'Counter-Strike-2-4.jpg'))

        conn.commit()
        conn.close()
        print("Veritabanı kontrolü tamamlandı.")
    except Exception as e:
        print(f"Veritabanı başlatılırken bir hata oluştu: {e}")

if __name__ == '__main__':
    init_db()