from flask import Flask, jsonify, render_template, request, redirect, url_for, send_from_directory, Response
from flask_cors import CORS
import sqlite3
import os
import json
import shutil
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import jwt
from datetime import datetime, timedelta
from functools import wraps
from database import init_db
from PIL import Image
import requests
import uuid
import subprocess

app = Flask(__name__)
app.config['SECRET_SECRET_KEY'] = 'bu-cok-gizli-bir-anahtar-kimse-bilmemeli'
app.config['SAVE_FOLDER'] = os.path.join(os.getcwd(), 'user_saves')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER_COVERS'] = os.path.join(BASE_DIR, 'static/images/covers')
app.config['UPLOAD_FOLDER_GALLERY'] = os.path.join(BASE_DIR, 'static/images/gallery')
app.config['UPLOAD_FOLDER_SLIDER'] = os.path.join(BASE_DIR, 'static/images/slider')
app.config['UPLOAD_FOLDER_BG'] = os.path.join(BASE_DIR, 'static/images/backgrounds')
app.config['UPLOAD_FOLDER_100_SAVES'] = os.path.join(BASE_DIR, 'yuzde_yuz_saves')
app.config['UPLOAD_FOLDER_LOGOS'] = os.path.join(BASE_DIR, 'static/images/logos')

DATABASE = 'kafe.db'

def json_response(data, status_code=200):
    response_data = json.dumps(data, ensure_ascii=False)
    return Response(response_data, status=status_code, content_type='application/json; charset=utf-8')

def get_db_connection():
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        if not token:
            return jsonify({'mesaj': 'Token eksik!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user_id = data['user_id']
        except:
            return jsonify({'mesaj': 'Token geçersiz veya süresi dolmuş!'}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated

def get_all_settings():
    conn = get_db_connection()
    settings_cursor = conn.execute('SELECT key, value FROM settings').fetchall()
    conn.close()
    return {row['key']: row['value'] for row in settings_cursor}

def set_setting(key, value):
    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def convert_to_webp(file, upload_folder, sub_folder=None):
    filename = secure_filename(file.filename)
    base, ext = os.path.splitext(filename)
    webp_filename = f"{base}.webp"
    
    if sub_folder and upload_folder == app.config['UPLOAD_FOLDER_GALLERY']:
        final_dir = os.path.join(upload_folder, sub_folder)
        if not os.path.exists(final_dir):
            os.makedirs(final_dir)
        file_path = os.path.join(final_dir, webp_filename)
        stored_path = os.path.join(sub_folder, webp_filename).replace('\\', '/')
    else:
        file_path = os.path.join(upload_folder, webp_filename)
        stored_path = webp_filename
        
    image = Image.open(file.stream)
    image.save(file_path, 'webp', quality=85)
    
    return stored_path

def get_gallery_folder_name(game_name):
    char_map = {
        'ğ': 'g', 'ı': 'i', 'ş': 's', 'ç': 'c', 'ö': 'o', 'ü': 'u',
        'Ğ': 'G', 'İ': 'I', 'Ş': 'S', 'Ç': 'C', 'Ö': 'O', 'Ü': 'U',
    }
    cleaned_name = "".join(char_map.get(char, char) for char in game_name)
    illegal_chars = ' <>:"/\\|?*'
    final_name = "".join(c for c in cleaned_name if c not in illegal_chars)
    return final_name.strip()

# --- LİSANS YÖNETİMİ BÖLÜMÜ ---
license_status_cache = {"status": None, "reason": "Henüz kontrol edilmedi", "last_checked": None}

def get_hwid():
    try:
        command = ['powershell', '-Command', 'Get-CimInstance -ClassName Win32_BaseBoard | Select-Object SerialNumber']
        process = subprocess.run(command, capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        lines = [line.strip() for line in process.stdout.splitlines() if line.strip()]
        if len(lines) >= 3 and lines[2] and lines[2] not in ['To be filled by O.E.M.', 'None']:
            return lines[2].replace(" ", "").strip()
    except Exception as e:
        print(f"Anakart Seri Numarası alınamadı: {e}")
    return ""

def get_public_ip_from_server():
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        if response.status_code == 200: return response.json()['ip']
    except requests.RequestException as e:
        print(f"Sunucu harici IP alınamadı: {e}")
    return ""

def check_license(license_key, hwid, client_ip):
    global license_status_cache
    api_url = "https://onurmedya.tr/burak/api.php"
    payload = {"license_key": license_key, "hwid": hwid, "client_ip": client_ip}
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            license_status_cache.update({
                'status': data.get('status'), 
                'reason': data.get('reason') or data.get('message', 'Durum bilinmiyor.'), 
                'full_api_response': data
            })
        else:
            license_status_cache.update({
                'status': 'invalid', 
                'reason': f'API sunucusuna ulaşılamadı (HTTP {response.status_code}).', 
                'full_api_response': {'debug': 'HTTP Status Error'}
            })
    except requests.RequestException as e:
        license_status_cache.update({
            'status': 'invalid', 
            'reason': f'API bağlantı hatası: {e}', 
            'full_api_response': {'debug': f'Request Exception: {str(e)}'}
        })
    license_status_cache['last_checked'] = datetime.now()
    return license_status_cache

def license_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        global license_status_cache
        settings = get_all_settings()
        license_key = settings.get('license_key', '')
        last_checked = license_status_cache.get('last_checked')
        time_to_recheck = not last_checked or (datetime.now() - last_checked) > timedelta(hours=1)
        
        if license_status_cache.get('status') != 'valid' or not license_key or time_to_recheck:
            if license_key:
                check_license(license_key, get_hwid(), get_public_ip_from_server())
            else:
                license_status_cache.update({'status': 'invalid', 'reason': 'Lisans Anahtarı Ayarlanmamış'})
                
        if license_status_cache.get('status') != 'valid':
            return redirect(url_for('license_management'))
        return f(*args, **kwargs)
    return decorated

# API Endpoints
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'): 
        return jsonify({"mesaj": "Kullanıcı adı veya şifre eksik"}), 400
    if len(data['username']) < 3: 
        return jsonify({"mesaj": "Kullanıcı adı en az 3 karakter olmalıdır."}), 400
    if len(data['password']) < 5: 
        return jsonify({"mesaj": "Şifre en az 5 karakter olmalıdır."}), 400
    
    conn = get_db_connection()
    if conn.execute('SELECT * FROM users WHERE username = ?', (data['username'],)).fetchone():
        conn.close()
        return jsonify({"mesaj": "Bu kullanıcı adı zaten alınmış."}), 409
    
    conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (data['username'], generate_password_hash(data['password'])))
    conn.commit()
    conn.close()
    return jsonify({"mesaj": "Kullanıcı başarıyla oluşturuldu! Şimdi giriş yapabilirsiniz."}), 201

@app.route('/api/login', methods=['POST'])
def login():
    auth_data = request.get_json()
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (auth_data['username'],)).fetchone()
    conn.close()
    if not user or not check_password_hash(user['password_hash'], auth_data['password']): 
        return jsonify({"mesaj": "Hatalı kullanıcı adı veya şifre"}), 401
    
    token = jwt.encode({'user_id': user['id'], 'exp': datetime.utcnow() + timedelta(hours=8)}, app.config['SECRET_KEY'], algorithm="HS256")
    return jsonify({'token': token})
    
@app.route('/api/games', methods=['GET'])
def get_games():
    conn = get_db_connection()
    limit = request.args.get('limit', type=int)
    
    query = """
        SELECT g.*, GROUP_CONCAT(c.name) as kategoriler
        FROM games g
        LEFT JOIN game_categories gc ON g.id = gc.game_id
        LEFT JOIN categories c ON gc.category_id = c.id
    """
    
    if limit:
        query += ' GROUP BY g.id ORDER BY g.id DESC LIMIT ?'
        games_cursor = conn.execute(query, (limit,)).fetchall()
    else:
        query += ' GROUP BY g.id ORDER BY g.oyun_adi ASC'
        games_cursor = conn.execute(query).fetchall()
        
    games_list = []
    for game in games_cursor:
        game_dict = dict(game)
        
        # DÜZELTİLMİŞ MANTIK
        kategoriler_str = game_dict.get('kategoriler')
        if kategoriler_str:
            game_dict['kategoriler'] = kategoriler_str.split(',')
        else:
            game_dict['kategoriler'] = []
            
        gallery_cursor = conn.execute('SELECT image_path FROM gallery_images WHERE game_id = ?', (game['id'],))
        game_dict['galeri'] = [row['image_path'] for row in gallery_cursor.fetchall()]
        games_list.append(game_dict)
        
    conn.close()
    return json_response(games_list)

@app.route('/api/categories', methods=['GET'])
def get_categories():
    conn = get_db_connection()
    categories_list = [dict(row) for row in conn.execute('SELECT id, name, icon FROM categories ORDER BY name ASC').fetchall()]
    conn.close()
    return json_response(categories_list)

@app.route('/api/slider', methods=['GET'])
def get_slider_data():
    conn = get_db_connection()
    sliders = [dict(row) for row in conn.execute('SELECT s.*, g.oyun_adi FROM slider s LEFT JOIN games g ON s.game_id = g.id WHERE s.is_active = 1 ORDER BY s.display_order ASC').fetchall()]
    conn.close()
    return json_response(sliders)

@app.route('/api/settings', methods=['GET'])
def get_settings_for_client():
    settings = get_all_settings()
    client_settings = {
        key: settings.get(key, '') for key in 
        ['cafe_name', 'slogan', 'logo_file', 'background_type', 'background_file', 'background_opacity_factor', 
         'primary_color_start', 'primary_color_end', 'welcome_modal_enabled', 'welcome_modal_text', 
         'social_google', 'social_instagram', 'social_facebook', 'social_youtube']
    }
    return json_response(client_settings)

@app.route('/api/user/ratings', methods=['GET'])
@token_required
def get_user_ratings(current_user_id):
    conn = get_db_connection()
    user_ratings = {str(row['game_id']): row['rating'] for row in conn.execute('SELECT game_id, rating FROM user_ratings WHERE user_id = ?', (current_user_id,)).fetchall()}
    conn.close()
    return json_response(user_ratings)

@app.route('/api/user/favorites', methods=['GET'])
@token_required
def get_user_favorites(current_user_id):
    conn = get_db_connection()
    user_favorites = [row['game_id'] for row in conn.execute('SELECT game_id FROM user_favorites WHERE user_id = ?', (current_user_id,)).fetchall()]
    conn.close()
    return json_response(user_favorites)

@app.route('/api/user/recently_played', methods=['GET'])
@token_required
def get_recently_played(current_user_id):
    conn = get_db_connection()
    query = """
        SELECT g.*, GROUP_CONCAT(c.name) as kategoriler
        FROM user_played_games upg
        JOIN games g ON upg.game_id = g.id
        LEFT JOIN game_categories gc ON g.id = gc.game_id
        LEFT JOIN categories c ON gc.category_id = c.id
        WHERE upg.user_id = ?
        GROUP BY g.id
        ORDER BY upg.played_at DESC
        LIMIT 24
    """
    games_cursor = conn.execute(query, (current_user_id,)).fetchall()
    games_list = []
    for game in games_cursor:
        game_dict = dict(game)
        kategoriler_str = game_dict.get('kategoriler')
        game_dict['kategoriler'] = kategoriler_str.split(',') if kategoriler_str else []
        games_list.append(game_dict)
    conn.close()
    return json_response(games_list)

@app.route('/api/user/saves', methods=['GET'])
@token_required
def get_user_saves(current_user_id):
    user_save_dir = os.path.join(app.config['SAVE_FOLDER'], str(current_user_id))
    if not os.path.exists(user_save_dir): 
        return jsonify([])
    try:
        saved_games = [int(f.split('.')[0]) for f in os.listdir(user_save_dir) if f.endswith('.zip') and f.split('.')[0].isdigit()]
        return json_response(saved_games)
    except Exception as e:
        return jsonify({'mesaj': f'Kayıtlar okunurken bir hata oluştu: {e}'}), 500

@app.route('/api/games/<int:game_id>/click', methods=['POST'])
def increment_click_count(game_id):
    conn = get_db_connection()
    conn.execute('UPDATE games SET click_count = click_count + 1 WHERE id = ?', (game_id,))
    conn.commit()
    conn.close()
    return jsonify({'mesaj': 'Tıklama sayısı artırıldı.'}), 200

@app.route('/api/games/<int:game_id>/played', methods=['POST'])
@token_required
def record_played_game(current_user_id, game_id):
    conn = get_db_connection()
    conn.execute('''
        INSERT OR REPLACE INTO user_played_games (user_id, game_id, played_at)
        VALUES (?, ?, ?)
    ''', (current_user_id, game_id, datetime.utcnow()))
    conn.commit()
    conn.close()
    return jsonify({'mesaj': 'Oynanma zamanı kaydedildi.'}), 200

@app.route('/api/games/<int:game_id>/rate', methods=['POST'])
@token_required
def rate_game(current_user_id, game_id):
    rating = request.get_json().get('rating')
    if rating is None or not (0.5 <= rating <= 5): 
        return jsonify({'mesaj': 'Geçersiz puan değeri.'}), 400
    
    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO user_ratings (user_id, game_id, rating) VALUES (?, ?, ?)', (current_user_id, game_id, rating))
    stats = conn.execute('SELECT AVG(rating), COUNT(rating) FROM user_ratings WHERE game_id = ?', (game_id,)).fetchone()
    new_avg, new_count = (stats[0] or 0, stats[1])
    conn.execute('UPDATE games SET average_rating = ?, rating_count = ? WHERE id = ?', (new_avg, new_count, game_id))
    conn.commit()
    conn.close()
    return jsonify({'mesaj': 'Puan kaydedildi.', 'average_rating': round(new_avg, 1), 'rating_count': new_count})

@app.route('/api/games/<int:game_id>/favorite', methods=['POST'])
@token_required
def toggle_favorite(current_user_id, game_id):
    conn = get_db_connection()
    if conn.execute('SELECT * FROM user_favorites WHERE user_id = ? AND game_id = ?', (current_user_id, game_id)).fetchone():
        conn.execute('DELETE FROM user_favorites WHERE user_id = ? AND game_id = ?', (current_user_id, game_id))
        new_status, message = False, "Oyun favorilerden kaldırıldı."
    else:
        conn.execute('INSERT INTO user_favorites (user_id, game_id) VALUES (?, ?)', (current_user_id, game_id))
        new_status, message = True, "Oyun favorilere eklendi."
    conn.commit()
    conn.close()
    return jsonify({'mesaj': message, 'is_favorite': new_status})

@app.route('/api/games/<int:game_id>/100save', methods=['GET'])
@token_required
def download_100_save(current_user_id, game_id):
    conn = get_db_connection()
    game = conn.execute('SELECT yuzde_yuz_save_path FROM games WHERE id = ?', (game_id,)).fetchone()
    conn.close()
    if not game or not game['yuzde_yuz_save_path']: 
        return jsonify({'mesaj': '%100 save dosyası bulunamadı.'}), 404
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER_100_SAVES'], game['yuzde_yuz_save_path'], as_attachment=True)
    except FileNotFoundError:
        return jsonify({'mesaj': 'Save dosyası sunucuda bulunamadı.'}), 404

# Admin Panel Routes
@app.route('/admin')
@license_required
def admin_index():
    conn = get_db_connection()
    stats = {
        'game_count': conn.execute('SELECT COUNT(*) FROM games').fetchone()[0],
        'category_count': conn.execute('SELECT COUNT(*) FROM categories').fetchone()[0],
        'user_count': conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    }
    query = "SELECT g.id, g.oyun_adi, GROUP_CONCAT(c.name) as category_names FROM games g LEFT JOIN game_categories gc ON g.id = gc.game_id LEFT JOIN categories c ON gc.category_id = c.id GROUP BY g.id ORDER BY g.id DESC LIMIT 5"
    recent_games = [dict(g) for g in conn.execute(query).fetchall()]
    conn.close()
    return render_template('index.html', stats=stats, recent_games=recent_games)

@app.route('/admin/games')
@license_required
def list_games():
    conn = get_db_connection()
    try:
        search_query = request.args.get('q', '') 
        
        # SORGULAMA: Tüm oyunları listelemeyi garanti eden robust yapı
        query = """
            SELECT 
                g.id, g.oyun_adi, g.aciklama, g.cover_image, g.youtube_id, g.save_yolu, g.calistirma_tipi, 
                g.calistirma_verisi, g.cikis_yili, g.pegi, g.oyun_dili, g.launch_script, g.yuzde_yuz_save_path,
                g.average_rating, g.rating_count, g.click_count,
                (
                    SELECT GROUP_CONCAT(c.name) 
                    FROM game_categories gc
                    JOIN categories c ON gc.category_id = c.id
                    WHERE gc.game_id = g.id
                ) AS category_names
            FROM games g
        """
        params = ()
        if search_query:
            query += " WHERE g.oyun_adi LIKE ?"
            params = ('%' + search_query + '%',)
        
        query += " ORDER BY g.id DESC"
        
        games_raw = conn.execute(query, params).fetchall()
        
        # NIHAI GÜVENLİK KONTROLÜ: Row objesini dict'e çevirip ID'si geçerli olanları alıyoruz.
        games_filtered = []
        for g_row in games_raw:
             g_dict = dict(g_row)
             # ID'si NULL veya 0 olmayan kayıtları listeye ekle
             if g_dict.get('id') is not None and g_dict.get('id') != 0:
                 games_filtered.append(g_dict)

        return render_template('manage_games.html', games=games_filtered, search_query=search_query)
    finally:
        if conn:
            conn.close() # Bağlantıyı kapat

@app.route('/admin/add', methods=['GET', 'POST'])
@license_required
def add_game():
    conn = get_db_connection()
    try: # Bağlantıyı güvence altına al
        if request.method == 'POST':
            form_data = request.form
            oyun_adi, aciklama, youtube_id, save_yolu, calistirma_tipi, cikis_yili, pegi, oyun_dili, launch_script = \
                (form_data.get(k) for k in ['oyun_adi', 'aciklama', 'youtube_id', 'save_yolu', 'calistirma_tipi', 'cikis_yili', 'pegi', 'oyun_dili', 'launch_script'])
            category_ids = request.form.getlist('category_ids')
            
            cover_image_filename = ''
            if 'cover_image' in request.files and request.files['cover_image'].filename:
                cover_image_filename = convert_to_webp(request.files['cover_image'], app.config['UPLOAD_FOLDER_COVERS'])
                
            yuzde_yuz_save_filename = ''
            if 'yuzde_yuz_save_file' in request.files and request.files['yuzde_yuz_save_file'].filename:
                file = request.files['yuzde_yuz_save_file']
                yuzde_yuz_save_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER_100_SAVES'], yuzde_yuz_save_filename))
                
            if calistirma_tipi == 'exe':
                calistirma_verisi = json.dumps({'yol': form_data.get('exe_yol'), 'argumanlar': form_data.get('exe_argumanlar', '')})
                
                # YENİ VARSAYILAN BETİK TANIMI BAŞLANGIÇ
                DEFAULT_LAUNCH_SCRIPT_CLEAN = """@echo off
set _EXE_PATH="%%EXE_YOLU%%"

:: *****************************************************************
:: * OYUN BAŞLATMA OTOMATİK SCRIPTİ
:: * Sunucu Tarafından Otomatik Üretilmiştir.
:: * %%EXE_YOLU%% (Tam Yol) ve %%EXE_ARGS%% (Argümanlar) değişkenleri kullanılmıştır.
:: *****************************************************************

:: 1. Kaynak Disk ve Dosya Yolu Bilgisi
echo Disk: %%~d_EXE_PATH%%
echo Oyun Klasörü: %%~p_EXE_PATH%%
echo EXE: %%~nx_EXE_PATH%%
echo Argümanlar: %%EXE_ARGS%%

:: 2. Örnek Registry Kaydı (Gerekliyse bu bloğu aktif edin)
:: REG ADD "HKCU\\Software\\OyunAdi" /v "KeyName" /t REG_SZ /d "Deger" /f

:: 3. Oyunu Başlat
start "" "%%EXE_YOLU%%" %%EXE_ARGS%%

:: NOT: Programı çalıştırmadan önce ek komutlar ekleyebilirsiniz.
"""

                # Eski varsayılanları kontrol etmek için örnekler
                old_default_content = """@echo off

:: *****************************************************************
:: * OYUN BAŞLATMA OTOMATİK SCRIPTİ
:: * Sunucu Tarafından Otomatik Üretilmiştir.
:: * %EXE_YOLU% ve %EXE_ARGS% değişkenleri otomatik doldurulur.
:: *****************************************************************

:: 1. Kaynak Disk ve Dosya Yolu Bilgisi
echo Oyun Yolu: %EXE_YOLU%
echo Argümanlar: %EXE_ARGS%

:: 2. Örnek Registry Kaydı (Gerekliyse bu bloğu aktif edin)
:: REG ADD "HKCU\Software\OyunAdi" /v "KeyName" /t REG_SZ /d "Deger" /f

:: 3. Oyunu Başlat
start "" "%EXE_YOLU%" %EXE_ARGS%

:: NOT: Programı çalıştırmadan önce ek komutlar ekleyebilirsiniz.
"""
                simple_old_default = 'start "" "%EXE_YOLU%" %EXE_ARGS%'
                
                # Eğer betik boşsa veya eski varsayılan içeriklerden biriyse yeni betiği kullan
                if not launch_script or launch_script.strip() in [simple_old_default, old_default_content.strip(), old_default_content.replace('\\', '').strip()]: 
                    launch_script = DEFAULT_LAUNCH_SCRIPT_CLEAN.strip()
                # YENİ VARSAYILAN BETİK TANIMI SONU
            else: # steam
                calistirma_verisi, launch_script = json.dumps({'app_id': form_data.get('steam_app_id')}), None
                
            cursor = conn.cursor()
            cursor.execute(''' INSERT INTO games(oyun_adi, aciklama, cover_image, youtube_id, save_yolu, calistirma_tipi, calistirma_verisi, cikis_yili, pegi, oyun_dili, launch_script, yuzde_yuz_save_path) 
                               VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ''', 
                           (oyun_adi, aciklama, cover_image_filename, youtube_id, save_yolu, calistirma_tipi, calistirma_verisi, cikis_yili, pegi, oyun_dili, launch_script, yuzde_yuz_save_filename))
            new_game_id = cursor.lastrowid
            
            # HATA DÜZELTME: category_ids listesindeki tekrar eden ID'leri kaldır ve int'e çevir
            if category_ids:
                # String ID'leri integer'a çevirip set ile benzersiz yap
                unique_category_ids = {int(cat_id) for cat_id in category_ids}
                # IntegrityError'ı kalıcı olarak çözmek için INSERT OR IGNORE kullan
                conn.executemany('INSERT OR IGNORE INTO game_categories (game_id, category_id) VALUES (?, ?)', [(new_game_id, cat_id) for cat_id in unique_category_ids])
            
            if 'gallery_images' in request.files:
                folder_name = get_gallery_folder_name(oyun_adi)
                for file in request.files.getlist('gallery_images'):
                    if file and file.filename:
                        path = convert_to_webp(file, app.config['UPLOAD_FOLDER_GALLERY'], sub_folder=folder_name)
                        conn.execute('INSERT INTO gallery_images (game_id, image_path) VALUES (?, ?)', (new_game_id, path))
            
            conn.commit()
            return redirect(url_for('list_games'))
            
        categories = conn.execute('SELECT * FROM categories ORDER BY name ASC').fetchall()
        return render_template('add_game.html', categories=categories)
    finally: # Bağlantı, ne olursa olsun burada kapatılır
        if conn:
            conn.close()

@app.route('/admin/edit/<int:game_id>', methods=['GET', 'POST'])
@license_required
def edit_game(game_id):
    conn = get_db_connection()
    try: # Bağlantıyı güvence altına al
        if request.method == 'POST':
            form_data = request.form
            oyun_adi, aciklama, youtube_id, save_yolu, calistirma_tipi, cikis_yili, pegi, oyun_dili, launch_script = \
                (form_data.get(k) for k in ['oyun_adi', 'aciklama', 'youtube_id', 'save_yolu', 'calistirma_tipi', 'cikis_yili', 'pegi', 'oyun_dili', 'launch_script'])
            category_ids = request.form.getlist('category_ids')
            
            cover_image_filename = form_data['current_cover_image']
            if 'cover_image' in request.files and request.files['cover_image'].filename:
                cover_image_filename = convert_to_webp(request.files['cover_image'], app.config['UPLOAD_FOLDER_COVERS'])
                
            yuzde_yuz_save_filename = form_data['current_yuzde_yuz_save_file']
            if 'yuzde_yuz_save_file' in request.files and request.files['yuzde_yuz_save_file'].filename:
                file = request.files['yuzde_yuz_save_file']
                yuzde_yuz_save_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER_100_SAVES'], yuzde_yuz_save_filename))
                
            folder_name = get_gallery_folder_name(oyun_adi)
            if request.form.getlist('delete_gallery'):
                for path in request.form.getlist('delete_gallery'):
                    conn.execute('DELETE FROM gallery_images WHERE image_path = ? AND game_id = ?', (path, game_id))
                    try: os.remove(os.path.join(app.config['UPLOAD_FOLDER_GALLERY'], path))
                    except OSError as e: print(f"Dosya silinemedi: {e}")
                    
            if 'gallery_images' in request.files:
                for file in request.files.getlist('gallery_images'):
                    if file and file.filename:
                        path = convert_to_webp(file, app.config['UPLOAD_FOLDER_GALLERY'], sub_folder=folder_name)
                        conn.execute('INSERT INTO gallery_images (game_id, image_path) VALUES (?, ?)', (game_id, path))
            
            if calistirma_tipi == 'exe':
                calistirma_verisi = json.dumps({'yol': form_data.get('exe_yol'), 'argumanlar': form_data.get('exe_argumanlar', '')})
                
                # YENİ VARSAYILAN BETİK TANIMI BAŞLANGIÇ
                DEFAULT_LAUNCH_SCRIPT_CLEAN = """@echo off
set _EXE_PATH="%%EXE_YOLU%%"

:: *****************************************************************
:: * OYUN BAŞLATMA OTOMATİK SCRIPTİ
:: * Sunucu Tarafından Otomatik Üretilmiştir.
:: * %%EXE_YOLU%% (Tam Yol) ve %%EXE_ARGS%% (Argümanlar) değişkenleri kullanılmıştır.
:: *****************************************************************

:: 1. Kaynak Disk ve Dosya Yolu Bilgisi
echo Disk: %%~d_EXE_PATH%%
echo Oyun Klasörü: %%~p_EXE_PATH%%
echo EXE: %%~nx_EXE_PATH%%
echo Argümanlar: %%EXE_ARGS%%

:: 2. Örnek Registry Kaydı (Gerekliyse bu bloğu aktif edin)
:: REG ADD "HKCU\\Software\\OyunAdi" /v "KeyName" /t REG_SZ /d "Deger" /f

:: 3. Oyunu Başlat
start "" "%%EXE_YOLU%%" %%EXE_ARGS%%

:: NOT: Programı çalıştırmadan önce ek komutlar ekleyebilirsiniz.
"""

                # Eski varsayılanları kontrol etmek için örnekler
                old_default_content = """@echo off

:: *****************************************************************
:: * OYUN BAŞLATMA OTOMATİK SCRIPTİ
:: * Sunucu Tarafından Otomatik Üretilmiştir.
:: * %EXE_YOLU% ve %EXE_ARGS% değişkenleri otomatik doldurulur.
:: *****************************************************************

:: 1. Kaynak Disk ve Dosya Yolu Bilgisi
echo Oyun Yolu: %EXE_YOLU%
echo Argümanlar: %EXE_ARGS%

:: 2. Örnek Registry Kaydı (Gerekliyse bu bloğu aktif edin)
:: REG ADD "HKCU\Software\OyunAdi" /v "KeyName" /t REG_SZ /d "Deger" /f

:: 3. Oyunu Başlat
start "" "%EXE_YOLU%" %EXE_ARGS%

:: NOT: Programı çalıştırmadan önce ek komutlar ekleyebilirsiniz.
"""
                simple_old_default = 'start "" "%EXE_YOLU%" %EXE_ARGS%'
                
                # Eğer betik boşsa veya eski varsayılan içeriklerden biriyse yeni betiği kullan
                if not launch_script or launch_script.strip() in [simple_old_default, old_default_content.strip(), old_default_content.replace('\\', '').strip()]:
                    launch_script = DEFAULT_LAUNCH_SCRIPT_CLEAN.strip()
                # YENİ VARSAYILAN BETİK TANIMI SONU
            else: # steam
                calistirma_verisi, launch_script = json.dumps({'app_id': form_data.get('steam_app_id')}), None
                
            sql = ''' UPDATE games SET oyun_adi=?, aciklama=?, cover_image=?, youtube_id=?, save_yolu=?, calistirma_tipi=?, calistirma_verisi=?, cikis_yili=?, pegi=?, oyun_dili=?, launch_script=?, yuzde_yuz_save_path=? WHERE id=? '''
            conn.execute(sql, (oyun_adi, aciklama, cover_image_filename, youtube_id, save_yolu, calistirma_tipi, calistirma_verisi, cikis_yili, pegi, oyun_dili, launch_script, yuzde_yuz_save_filename, game_id))
            
            conn.execute('DELETE FROM game_categories WHERE game_id = ?', (game_id,))
            # HATA DÜZELTME: category_ids listesindeki tekrar eden ID'leri kaldır ve int'e çevir
            if category_ids:
                unique_category_ids = {int(cat_id) for cat_id in category_ids} # Set comprehension ile benzersiz ID'leri topla
                # IntegrityError'ı kalıcı olarak çözmek için INSERT OR IGNORE kullan
                conn.executemany('INSERT OR IGNORE INTO game_categories (game_id, category_id) VALUES (?, ?)', [(game_id, cat_id) for cat_id in unique_category_ids])
            # HATA DÜZELTME SONU
                    
            conn.commit()
            return redirect(url_for('list_games'))
            
        game = conn.execute('SELECT * FROM games WHERE id = ?', (game_id,)).fetchone()
        if not game: return "Oyun bulunamadı!", 404
        
        game_data = dict(game)
        game_data['calistirma_verisi_dict'] = json.loads(game['calistirma_verisi'] or '{}')
        categories = conn.execute('SELECT * FROM categories ORDER BY name ASC').fetchall()
        gallery_images = conn.execute('SELECT * FROM gallery_images WHERE game_id = ?', (game_id,)).fetchall()
        game_category_ids = {row['category_id'] for row in conn.execute('SELECT category_id FROM game_categories WHERE game_id = ?', (game_id,)).fetchall()}
        
        return render_template('edit_game.html', game=game_data, categories=categories, gallery=gallery_images, game_category_ids=game_category_ids)
    finally: # Bağlantı, ne olursa olsun burada kapatılır
        if conn:
            conn.close()

@app.route('/admin/delete/<int:game_id>', methods=['POST'])
@license_required
def delete_game(game_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM games WHERE id = ?', (game_id,))
        conn.commit()
        return redirect(url_for('list_games'))
    finally:
        if conn:
            conn.close()


@app.route('/admin/categories', methods=['GET', 'POST'])
@license_required
def manage_categories():
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            category_name = request.form['name']
            category_icon = request.form.get('icon', '🎮')
            if category_name:
                try:
                    conn.execute('INSERT INTO categories (name, icon) VALUES (?, ?)', (category_name, category_icon))
                    conn.commit()
                except sqlite3.IntegrityError: pass
            return redirect(url_for('manage_categories'))
        categories = conn.execute('SELECT * FROM categories ORDER BY name ASC').fetchall()
        return render_template('manage_categories.html', categories=categories)
    finally:
        if conn:
            conn.close()

@app.route('/admin/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@license_required
def edit_category(category_id):
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            new_name = request.form['name']
            new_icon = request.form.get('icon', '🎮')
            if new_name:
                conn.execute('UPDATE categories SET name = ?, icon = ? WHERE id = ?', (new_name, new_icon, category_id))
                conn.commit()
            return redirect(url_for('manage_categories'))
        category = conn.execute('SELECT * FROM categories WHERE id = ?', (category_id,)).fetchone()
        if not category: return "Kategori bulunamadı!", 404
        return render_template('edit_category.html', category=category)
    finally:
        if conn:
            conn.close()

@app.route('/admin/categories/delete/<int:category_id>', methods=['POST'])
@license_required
def delete_category(category_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM categories WHERE id = ?', (category_id,))
        conn.commit()
        return redirect(url_for('manage_categories'))
    finally:
        if conn:
            conn.close()

@app.route('/admin/users')
@license_required
def manage_users():
    conn = get_db_connection()
    try:
        users = conn.execute('SELECT id, username FROM users ORDER BY username ASC').fetchall()
        return render_template('manage_users.html', users=users)
    finally:
        if conn:
            conn.close()

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@license_required
def edit_user(user_id):
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            new_username = request.form.get('username', '').strip()
            new_password = request.form.get('new_password', '')
            if new_username and len(new_username) >= 3:
                if not conn.execute('SELECT id FROM users WHERE username = ? AND id != ?', (new_username, user_id)).fetchone():
                    conn.execute('UPDATE users SET username = ? WHERE id = ?', (new_username, user_id))
                    conn.commit()
            if new_password and len(new_password) >= 5:
                conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (generate_password_hash(new_password), user_id))
                conn.commit()
            return redirect(url_for('manage_users'))
        user = conn.execute('SELECT id, username FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user: return "Kullanıcı bulunamadı!", 404
        return render_template('edit_user.html', user=user)
    finally:
        if conn:
            conn.close()

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@license_required
def delete_user(user_id):
    if user_id == 1: 
        return redirect(url_for('manage_users'))
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        user_save_dir = os.path.join(app.config['SAVE_FOLDER'], str(user_id))
        if os.path.exists(user_save_dir): 
            shutil.rmtree(user_save_dir)
        return redirect(url_for('manage_users'))
    finally:
        if conn:
            conn.close()

@app.route('/admin/sliders')
@license_required
def manage_sliders():
    conn = get_db_connection()
    try:
        sliders = conn.execute('SELECT s.*, g.oyun_adi FROM slider s LEFT JOIN games g ON s.game_id = g.id ORDER BY s.display_order ASC').fetchall()
        return render_template('manage_sliders.html', sliders=sliders)
    finally:
        if conn:
            conn.close()

@app.route('/admin/slider/add', methods=['GET', 'POST'])
@license_required
def add_slider():
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            form = request.form
            bg_image = ''
            if 'background_image' in request.files and request.files['background_image'].filename:
                bg_image = convert_to_webp(request.files['background_image'], app.config['UPLOAD_FOLDER_SLIDER'])
            
            conn.execute('''INSERT INTO slider (game_id, badge_text, title, description, background_image, is_active, display_order) 
                            VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                           (form.get('game_id') or None, form.get('badge_text'), form.get('title'), form.get('description'), 
                            bg_image, 1 if 'is_active' in form else 0, form.get('display_order', 0)))
            conn.commit()
            return redirect(url_for('manage_sliders'))
        
        games = conn.execute('SELECT id, oyun_adi FROM games ORDER BY oyun_adi ASC').fetchall()
        return render_template('add_slider.html', games=games)
    finally:
        if conn:
            conn.close()

@app.route('/admin/slider/edit/<int:slider_id>', methods=['GET', 'POST'])
@license_required
def edit_slider(slider_id):
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            form = request.form
            bg_image = form.get('current_background_image')
            if 'background_image' in request.files and request.files['background_image'].filename:
                if bg_image:
                    try: os.remove(os.path.join(app.config['UPLOAD_FOLDER_SLIDER'], bg_image))
                    except OSError: pass
                bg_image = convert_to_webp(request.files['background_image'], app.config['UPLOAD_FOLDER_SLIDER'])
                
            conn.execute('''UPDATE slider SET game_id=?, badge_text=?, title=?, description=?, background_image=?, is_active=?, display_order=? 
                            WHERE id=?''', 
                           (form.get('game_id') or None, form.get('badge_text'), form.get('title'), form.get('description'), 
                            bg_image, 1 if 'is_active' in form else 0, form.get('display_order', 0), slider_id))
            conn.commit()
            return redirect(url_for('manage_sliders'))
        
        slider = conn.execute('SELECT * FROM slider WHERE id = ?', (slider_id,)).fetchone()
        games = conn.execute('SELECT id, oyun_adi FROM games ORDER BY oyun_adi ASC').fetchall()
        return render_template('edit_slider.html', slider=slider, games=games)
    finally:
        if conn:
            conn.close()

@app.route('/admin/slider/delete/<int:slider_id>', methods=['POST'])
@license_required
def delete_slider(slider_id):
    conn = get_db_connection()
    try:
        slider = conn.execute('SELECT background_image FROM slider WHERE id = ?', (slider_id,)).fetchone()
        if slider and slider['background_image']:
            try: os.remove(os.path.join(app.config['UPLOAD_FOLDER_SLIDER'], slider['background_image']))
            except OSError: pass
        conn.execute('DELETE FROM slider WHERE id = ?', (slider_id,))
        conn.commit()
        return redirect(url_for('manage_sliders'))
    finally:
        if conn:
            conn.close()

@app.route('/admin/ratings')
@license_required
def manage_ratings():
    sort_by, order = request.args.get('sort_by', 'oyun_adi'), request.args.get('order', 'asc')
    if sort_by not in ['oyun_adi', 'average_rating', 'rating_count']: sort_by = 'oyun_adi'
    if order not in ['asc', 'desc']: order = 'asc'
    conn = get_db_connection()
    try:
        games = conn.execute(f"SELECT id, oyun_adi, average_rating, rating_count FROM games ORDER BY {sort_by} {order}").fetchall()
        return render_template('manage_ratings.html', games=games, sort_by=sort_by, next_order='desc' if order == 'asc' else 'asc')
    finally:
        if conn:
            conn.close()

@app.route('/admin/statistics')
@license_required
def manage_statistics():
    sort_by, order = request.args.get('sort_by', 'click_count'), request.args.get('order', 'desc')
    if sort_by not in ['oyun_adi', 'click_count']: sort_by = 'click_count'
    if order not in ['asc', 'desc']: order = 'desc'
    conn = get_db_connection()
    try:
        games = conn.execute(f"SELECT id, oyun_adi, click_count FROM games ORDER BY {sort_by} {order}").fetchall()
        return render_template('manage_statistics.html', games=games, sort_by=sort_by, next_order='desc' if order == 'asc' else 'asc')
    finally:
        if conn:
            conn.close()

@app.route('/admin/statistics/reset_all', methods=['POST'])
@license_required
def reset_all_clicks():
    conn = get_db_connection()
    try:
        conn.execute('UPDATE games SET click_count = 0')
        conn.commit()
        return redirect(url_for('manage_statistics'))
    finally:
        if conn:
            conn.close()

@app.route('/admin/ratings/reset_all', methods=['POST'])
@license_required
def reset_all_ratings():
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM user_ratings')
        conn.execute('UPDATE games SET average_rating = 0, rating_count = 0')
        conn.commit()
        return redirect(url_for('manage_ratings'))
    finally:
        if conn:
            conn.close()

@app.route('/admin/download_games')
@license_required
def download_games():
    return render_template('download_games.html')

@app.route('/admin/license_management', methods=['GET', 'POST'])
def license_management():
    settings = get_all_settings()
    license_key = settings.get('license_key', '')
    server_hwid, server_public_ip, message = get_hwid(), get_public_ip_from_server(), None
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'save_and_check':
            license_key = request.form.get('license_key', '')
            set_setting('license_key', license_key)
            check_license(license_key, server_hwid, server_public_ip)
            message = "Lisans kaydedildi ve doğrulandı!" if license_status_cache['status'] == 'valid' else f"Doğrulanamadı: {license_status_cache['reason']}"
        elif action == 'check_only':
            if license_key:
                check_license(license_key, server_hwid, server_public_ip)
                message = f"Durum: {license_status_cache['reason']}"
            else:
                message = "Önce bir lisans anahtarı kaydedin."
                
    return render_template('license_management.html', 
                           license_key=license_key, 
                           license_status=license_status_cache.get('status'), 
                           license_reason=license_status_cache.get('reason'), 
                           server_hwid=server_hwid, message=message, 
                           full_license_data=license_status_cache.get('full_api_response', {}), 
                           last_check_time=license_status_cache.get('last_checked'))

@app.route('/admin/social_media', methods=['GET', 'POST'])
@license_required
def social_media_settings():
    if request.method == 'POST':
        for key in ['social_google', 'social_instagram', 'social_facebook', 'social_youtube']:
            set_setting(key, request.form.get(key, ''))
        return redirect(url_for('social_media_settings'))
    
    settings = get_all_settings()
    return render_template('social_media_settings.html', settings=settings)

@app.route('/admin/settings', methods=['GET', 'POST'])
@license_required
def general_settings():
    if request.method == 'POST':
        if 'delete_logo' in request.form:
            logo_to_delete = get_all_settings().get('logo_file')
            if logo_to_delete:
                try: os.remove(os.path.join(app.config['UPLOAD_FOLDER_LOGOS'], logo_to_delete))
                except OSError as e: print(f"Logo silinemedi: {e}")
            set_setting('logo_file', '')
        else:
            for key in ['cafe_name', 'slogan', 'background_type', 'primary_color_start', 'primary_color_end', 'welcome_modal_text']:
                set_setting(key, request.form.get(key))
                
            set_setting('welcome_modal_enabled', '1' if 'welcome_modal_enabled' in request.form else '0')
            try:
                opacity = f"{max(0.1, min(1.0, float(request.form.get('background_opacity_factor', '1.0')))):.1f}"
                set_setting('background_opacity_factor', opacity)
            except ValueError:
                set_setting('background_opacity_factor', '1.0')

            if 'logo_file' in request.files and request.files['logo_file'].filename:
                file = request.files['logo_file']
                old_file = get_all_settings().get('logo_file')
                if old_file:
                    try: os.remove(os.path.join(app.config['UPLOAD_FOLDER_LOGOS'], old_file))
                    except OSError: pass
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER_LOGOS'], filename))
                set_setting('logo_file', filename)

            if request.form['background_type'] == 'custom_bg' and 'custom_background_file' in request.files and request.files['custom_background_file'].filename:
                file = request.files['custom_background_file']
                old_file = get_all_settings().get('background_file')
                if old_file:
                    try: os.remove(os.path.join(app.config['UPLOAD_FOLDER_BG'], old_file))
                    except OSError: pass
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER_BG'], filename))
                set_setting('background_file', filename)
            elif request.form['background_type'] == 'default':
                old_file = get_all_settings().get('background_file')
                if old_file:
                    try: os.remove(os.path.join(app.config['UPLOAD_FOLDER_BG'], old_file))
                    except OSError: pass
                set_setting('background_file', '')
                
        return redirect(url_for('general_settings'))

    settings = get_all_settings()
    return render_template('general_settings.html', settings=settings)

@app.route('/api/internal/check_status')
def check_status_for_client():
    global license_status_cache
    last_checked = license_status_cache.get('last_checked')
    if not last_checked or (datetime.now() - last_checked) > timedelta(hours=1):
        license_key = get_all_settings().get('license_key', '')
        if license_key:
            check_license(license_key, get_hwid(), get_public_ip_from_server())

    if license_status_cache.get('status') == 'valid':
        return jsonify({"status": "ok"})
    else:
        full_response = license_status_cache.get('full_api_response', {})
        full_response['status'] = 'error'
        return jsonify(full_response), 403

if __name__ == '__main__':
    init_db()
    for folder_key in ['UPLOAD_FOLDER_COVERS', 'UPLOAD_FOLDER_GALLERY', 'SAVE_FOLDER', 'UPLOAD_FOLDER_BG', 'UPLOAD_FOLDER_100_SAVES', 'UPLOAD_FOLDER_LOGOS', 'UPLOAD_FOLDER_SLIDER']:
        folder_path = app.config.get(folder_key)
        if folder_path and not os.path.exists(folder_path):
            os.makedirs(folder_path)
    app.run(debug=True, host='0.0.0.0', port=5000)