from flask import Flask, jsonify, render_template, request, redirect, url_for, send_from_directory
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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bu-cok-gizli-bir-anahtar-kimse-bilmemeli'
app.config['SAVE_FOLDER'] = os.path.join(os.getcwd(), 'user_saves')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER_COVERS'] = os.path.join(BASE_DIR, 'static/images/covers')
app.config['UPLOAD_FOLDER_GALLERY'] = os.path.join(BASE_DIR, 'static/images/gallery')
app.config['UPLOAD_FOLDER_BG'] = os.path.join(BASE_DIR, 'static/images/backgrounds') 
app.config['UPLOAD_FOLDER_100_SAVES'] = os.path.join(BASE_DIR, 'yuzde_yuz_saves')

DATABASE = 'kafe.db'

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

# API Endpoints
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'): return jsonify({"mesaj": "Kullanıcı adı veya şifre eksik"}), 400
    if len(data['username']) < 3: return jsonify({"mesaj": "Kullanıcı adı en az 3 karakter olmalıdır."}), 400
    if len(data['password']) < 5: return jsonify({"mesaj": "Şifre en az 5 karakter olmalıdır."}), 400
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (data['username'],)).fetchone()
    if user:
        conn.close()
        return jsonify({"mesaj": "Bu kullanıcı adı zaten alınmış."}), 409
    password_hash = generate_password_hash(data['password'])
    conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (data['username'], password_hash))
    conn.commit()
    conn.close()
    return jsonify({"mesaj": "Kullanıcı başarıyla oluşturuldu! Şimdi giriş yapabilirsiniz."}), 201

@app.route('/api/login', methods=['POST'])
def login():
    auth_data = request.get_json()
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (auth_data['username'],)).fetchone()
    conn.close()
    if not user or not check_password_hash(user['password_hash'], auth_data['password']): return jsonify({"mesaj": "Hatalı kullanıcı adı veya şifre"}), 401
    token = jwt.encode({'user_id': user['id'], 'exp': datetime.utcnow() + timedelta(hours=8)}, app.config['SECRET_KEY'], algorithm="HS256")
    return jsonify({'token': token})
    
@app.route('/api/games', methods=['GET'])
def get_games():
    conn = get_db_connection()
    games_cursor = conn.execute('SELECT g.*, c.name as kategori FROM games g LEFT JOIN categories c ON g.category_id = c.id ORDER BY g.oyun_adi ASC').fetchall()
    games_list = []
    for game in games_cursor:
        game_dict = dict(game)
        gallery_cursor = conn.execute('SELECT image_path FROM gallery_images WHERE game_id = ?', (game['id'],))
        gallery_images = [row['image_path'] for row in gallery_cursor.fetchall()]
        game_dict['galeri'] = gallery_images
        games_list.append(game_dict)
    conn.close()
    return jsonify(games_list)

@app.route('/api/categories', methods=['GET'])
def get_categories():
    conn = get_db_connection()
    categories_cursor = conn.execute('SELECT name FROM categories ORDER BY name ASC').fetchall()
    conn.close()
    categories_list = [row['name'] for row in categories_cursor]
    return jsonify(categories_list)

@app.route('/api/settings', methods=['GET'])
def get_settings_for_client():
    settings = get_all_settings()
    return jsonify({
        'cafe_name': settings.get('cafe_name'),
        'slogan': settings.get('slogan'),
        'background_type': settings.get('background_type'),
        'background_file': settings.get('background_file'),
        'background_opacity_factor': settings.get('background_opacity_factor'),
        'primary_color_start': settings.get('primary_color_start'),
        'primary_color_end': settings.get('primary_color_end')
    })

@app.route('/api/user/ratings', methods=['GET'])
@token_required
def get_user_ratings(current_user_id):
    conn = get_db_connection()
    ratings_cursor = conn.execute('SELECT game_id, rating FROM user_ratings WHERE user_id = ?', (current_user_id,)).fetchall()
    conn.close()
    user_ratings = {str(row['game_id']): row['rating'] for row in ratings_cursor}
    return jsonify(user_ratings)

@app.route('/api/user/favorites', methods=['GET'])
@token_required
def get_user_favorites(current_user_id):
    conn = get_db_connection()
    favorites_cursor = conn.execute('SELECT game_id FROM user_favorites WHERE user_id = ?', (current_user_id,)).fetchall()
    conn.close()
    user_favorites = [row['game_id'] for row in favorites_cursor]
    return jsonify(user_favorites)

@app.route('/api/user/saves', methods=['GET'])
@token_required
def get_user_saves(current_user_id):
    user_save_dir = os.path.join(app.config['SAVE_FOLDER'], str(current_user_id))
    if not os.path.exists(user_save_dir):
        return jsonify([])
    try:
        saved_games = []
        for filename in os.listdir(user_save_dir):
            if filename.endswith('.zip'):
                game_id = os.path.splitext(filename)[0]
                if game_id.isdigit():
                    saved_games.append(int(game_id))
        return jsonify(saved_games)
    except Exception as e:
        return jsonify({'mesaj': f'Kayıtlar okunurken bir hata oluştu: {e}'}), 500

@app.route('/api/games/<int:game_id>/click', methods=['POST'])
def increment_click_count(game_id):
    conn = get_db_connection()
    conn.execute('UPDATE games SET click_count = click_count + 1 WHERE id = ?', (game_id,))
    conn.commit()
    conn.close()
    return jsonify({'mesaj': 'Tıklama sayısı artırıldı.'}), 200

@app.route('/api/games/<int:game_id>/rate', methods=['POST'])
@token_required
def rate_game(current_user_id, game_id):
    data = request.get_json()
    rating = data.get('rating')
    if rating is None or not (0.5 <= rating <= 5): return jsonify({'mesaj': 'Geçersiz puan değeri.'}), 400
    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO user_ratings (user_id, game_id, rating) VALUES (?, ?, ?)', (current_user_id, game_id, rating))
    stats_cursor = conn.execute('SELECT AVG(rating), COUNT(rating) FROM user_ratings WHERE game_id = ?', (game_id,)).fetchone()
    new_avg_rating = stats_cursor[0] if stats_cursor[0] is not None else 0
    new_rating_count = stats_cursor[1]
    conn.execute('UPDATE games SET average_rating = ?, rating_count = ? WHERE id = ?', (new_avg_rating, new_rating_count, game_id))
    conn.commit()
    conn.close()
    return jsonify({'mesaj': 'Puan başarıyla kaydedildi.', 'average_rating': round(new_avg_rating, 1), 'rating_count': new_rating_count})

@app.route('/api/games/<int:game_id>/favorite', methods=['POST'])
@token_required
def toggle_favorite(current_user_id, game_id):
    conn = get_db_connection()
    is_favorite = conn.execute('SELECT * FROM user_favorites WHERE user_id = ? AND game_id = ?', (current_user_id, game_id)).fetchone()
    if is_favorite:
        conn.execute('DELETE FROM user_favorites WHERE user_id = ? AND game_id = ?', (current_user_id, game_id))
        new_status = False
        message = "Oyun favorilerden kaldırıldı."
    else:
        conn.execute('INSERT INTO user_favorites (user_id, game_id) VALUES (?, ?)', (current_user_id, game_id))
        new_status = True
        message = "Oyun favorilere eklendi."
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
        return jsonify({'mesaj': 'Bu oyun için %100 save dosyası bulunamadı.'}), 404
    
    try:
        return send_from_directory(
            app.config['UPLOAD_FOLDER_100_SAVES'],
            game['yuzde_yuz_save_path'],
            as_attachment=True
        )
    except FileNotFoundError:
        return jsonify({'mesaj': 'Save dosyası sunucuda bulunamadı.'}), 404

# Admin Panel Routes
@app.route('/admin')
def admin_index():
    conn = get_db_connection()
    
    game_count = conn.execute('SELECT COUNT(*) FROM games').fetchone()[0]
    category_count = conn.execute('SELECT COUNT(*) FROM categories').fetchone()[0]
    user_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    stats = {
        'game_count': game_count,
        'category_count': category_count,
        'user_count': user_count
    }

    query = """
    SELECT g.id, g.oyun_adi, c.name as category_name
    FROM games g
    LEFT JOIN categories c ON g.category_id = c.id
    ORDER BY g.id DESC
    LIMIT 5
    """
    recent_games = conn.execute(query).fetchall()
    conn.close()
    
    recent_games_list = [dict(game) for game in recent_games]
    
    return render_template('index.html', stats=stats, recent_games=recent_games_list)

@app.route('/admin_redirect')
def admin_redirect():
    return redirect(url_for('admin_index'))

@app.route('/admin/games')
def list_games():
    search_query = request.args.get('q', '') 
    conn = get_db_connection()
    if search_query:
        query = "SELECT g.*, c.name as category_name FROM games g LEFT JOIN categories c ON g.category_id = c.id WHERE g.oyun_adi LIKE ? ORDER BY g.id DESC"
        games_raw = conn.execute(query, ('%' + search_query + '%',)).fetchall()
    else:
        query = "SELECT g.*, c.name as category_name FROM games g LEFT JOIN categories c ON g.category_id = c.id ORDER BY g.id DESC"
        games_raw = conn.execute(query).fetchall()
    conn.close()
    return render_template('manage_games.html', games=games_raw, search_query=search_query)

@app.route('/admin/add', methods=['GET', 'POST'])
def add_game():
    conn = get_db_connection()
    if request.method == 'POST':
        oyun_adi = request.form['oyun_adi']; aciklama = request.form['aciklama']; youtube_id = request.form['youtube_id']; save_yolu = request.form['save_yolu']; calistirma_tipi = request.form['calistirma_tipi']; cikis_yili = request.form['cikis_yili']; pegi = request.form['pegi']; category_id = request.form.get('category_id') or None;
        launch_script = request.form.get('launch_script')
        
        cover_image_filename = ''
        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file and file.filename != '':
                cover_image_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER_COVERS'], cover_image_filename))
        
        yuzde_yuz_save_filename = ''
        if 'yuzde_yuz_save_file' in request.files:
            file = request.files['yuzde_yuz_save_file']
            if file and file.filename != '':
                yuzde_yuz_save_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER_100_SAVES'], yuzde_yuz_save_filename))

        calistirma_verisi = {}
        if calistirma_tipi == 'exe':
            calistirma_verisi = {'yol': request.form.get('exe_yol'), 'argumanlar': request.form.get('exe_argumanlar', '')}
            if not launch_script or launch_script.strip() == '':
                launch_script = f'start "" "%EXE_YOLU%" %EXE_ARGS%'
        elif calistirma_tipi == 'steam':
            calistirma_verisi = {'app_id': request.form.get('steam_app_id')}
            launch_script = None 
        
        sql = ''' INSERT INTO games(oyun_adi, aciklama, cover_image, youtube_id, save_yolu, calistirma_tipi, calistirma_verisi, cikis_yili, pegi, category_id, launch_script, yuzde_yuz_save_path) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) '''
        cursor = conn.cursor()
        cursor.execute(sql, (oyun_adi, aciklama, cover_image_filename, youtube_id, save_yolu, calistirma_tipi, json.dumps(calistirma_verisi), cikis_yili, pegi, category_id, launch_script, yuzde_yuz_save_filename))
        
        new_game_id = cursor.lastrowid
        if 'gallery_images' in request.files:
            files = request.files.getlist('gallery_images')
            for file in files:
                if file and file.filename != '':
                    gallery_filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER_GALLERY'], gallery_filename))
                    conn.execute('INSERT INTO gallery_images (game_id, image_path) VALUES (?, ?)', (new_game_id, gallery_filename))
        
        conn.commit()
        conn.close()
        return redirect(url_for('list_games'))
    
    categories = conn.execute('SELECT * FROM categories ORDER BY name ASC').fetchall()
    conn.close()
    return render_template('add_game.html', categories=categories)

@app.route('/admin/edit/<int:game_id>', methods=['GET', 'POST'])
def edit_game(game_id):
    conn = get_db_connection()
    if request.method == 'POST':
        oyun_adi = request.form['oyun_adi']; aciklama = request.form['aciklama']; youtube_id = request.form['youtube_id']; save_yolu = request.form['save_yolu']; calistirma_tipi = request.form['calistirma_tipi']; cikis_yili = request.form['cikis_yili']; pegi = request.form['pegi']; category_id = request.form.get('category_id') or None
        launch_script = request.form.get('launch_script')

        cover_image_filename = request.form['current_cover_image']
        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file and file.filename != '':
                cover_image_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER_COVERS'], cover_image_filename))
        
        yuzde_yuz_save_filename = request.form['current_yuzde_yuz_save_file']
        if 'yuzde_yuz_save_file' in request.files:
            file = request.files['yuzde_yuz_save_file']
            if file and file.filename != '':
                yuzde_yuz_save_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER_100_SAVES'], yuzde_yuz_save_filename))

        images_to_delete = request.form.getlist('delete_gallery')
        if images_to_delete:
            for image_path_to_delete in images_to_delete:
                conn.execute('DELETE FROM gallery_images WHERE image_path = ? AND game_id = ?', (image_path_to_delete, game_id))
                try: os.remove(os.path.join(app.config['UPLOAD_FOLDER_GALLERY'], image_path_to_delete))
                except OSError as e: print(f"Dosya silinirken hata: {e}")
        
        if 'gallery_images' in request.files:
            files = request.files.getlist('gallery_images')
            for file in files:
                if file and file.filename != '':
                    gallery_filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER_GALLERY'], gallery_filename))
                    conn.execute('INSERT INTO gallery_images (game_id, image_path) VALUES (?, ?)', (game_id, gallery_filename))
        
        calistirma_verisi = {}
        if calistirma_tipi == 'exe':
            calistirma_verisi = {'yol': request.form.get('exe_yol'), 'argumanlar': request.form.get('exe_argumanlar', '')}
            if not launch_script or launch_script.strip() == '':
                launch_script = f'start "" "%EXE_YOLU%" %EXE_ARGS%'
        elif calistirma_tipi == 'steam':
            calistirma_verisi = {'app_id': request.form.get('steam_app_id')}
            launch_script = None 
        
        sql = ''' UPDATE games SET oyun_adi=?, aciklama=?, cover_image=?, youtube_id=?, save_yolu=?, calistirma_tipi=?, calistirma_verisi=?, cikis_yili=?, pegi=?, category_id=?, launch_script=?, yuzde_yuz_save_path=? WHERE id=? '''
        conn.execute(sql, (oyun_adi, aciklama, cover_image_filename, youtube_id, save_yolu, calistirma_tipi, json.dumps(calistirma_verisi), cikis_yili, pegi, category_id, launch_script, yuzde_yuz_save_filename, game_id))
        
        conn.commit()
        conn.close()
        return redirect(url_for('list_games'))
    
    game = conn.execute('SELECT * FROM games WHERE id = ?', (game_id,)).fetchone()
    categories = conn.execute('SELECT * FROM categories ORDER BY name ASC').fetchall()
    gallery_images = conn.execute('SELECT * FROM gallery_images WHERE game_id = ?', (game_id,)).fetchall()
    conn.close()
    
    if game is None: return "Oyun bulunamadı!", 404
    
    game_data = dict(game)
    game_data['calistirma_verisi_dict'] = json.loads(game['calistirma_verisi']) if game['calistirma_verisi'] else {}
    return render_template('edit_game.html', game=game_data, categories=categories, gallery=gallery_images)

@app.route('/admin/delete/<int:game_id>', methods=['POST'])
def delete_game(game_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM gallery_images WHERE game_id = ?', (game_id,))
    conn.execute('DELETE FROM games WHERE id = ?', (game_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('list_games'))

@app.route('/admin/categories', methods=['GET', 'POST'])
def manage_categories():
    conn = get_db_connection()
    if request.method == 'POST':
        category_name = request.form['name']
        if category_name:
            try:
                conn.execute('INSERT INTO categories (name) VALUES (?)', (category_name,))
                conn.commit()
            except sqlite3.IntegrityError: pass
        return redirect(url_for('manage_categories'))
    categories = conn.execute('SELECT * FROM categories ORDER BY name ASC').fetchall()
    conn.close()
    return render_template('manage_categories.html', categories=categories)

@app.route('/admin/categories/delete/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    conn = get_db_connection()
    conn.execute('UPDATE games SET category_id = NULL WHERE category_id = ?', (category_id,))
    conn.execute('DELETE FROM categories WHERE id = ?', (category_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('manage_categories'))

@app.route('/admin/users')
def manage_users():
    conn = get_db_connection()
    users = conn.execute('SELECT id, username FROM users ORDER BY username ASC').fetchall()
    conn.close()
    return render_template('manage_users.html', users=users)

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    conn = get_db_connection()
    if request.method == 'POST':
        new_username = request.form.get('username').strip()
        new_password = request.form.get('new_password')

        if new_username and len(new_username) >= 3:
            existing_user = conn.execute('SELECT id FROM users WHERE username = ? AND id != ?', (new_username, user_id)).fetchone()
            if not existing_user:
                conn.execute('UPDATE users SET username = ? WHERE id = ?', (new_username, user_id))
                conn.commit()
            else:
                print(f"Hata: '{new_username}' kullanıcı adı zaten alınmış.")

        if new_password and len(new_password) >= 5:
            password_hash = generate_password_hash(new_password)
            conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
            conn.commit()

        conn.close()
        return redirect(url_for('manage_users'))

    user = conn.execute('SELECT id, username FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user is None: return "Kullanıcı bulunamadı!", 404
    return render_template('edit_user.html', user=user)

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if user_id == 1:
        return redirect(url_for('manage_users'))
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    user_save_dir = os.path.join(app.config['SAVE_FOLDER'], str(user_id))
    if os.path.exists(user_save_dir):
        shutil.rmtree(user_save_dir)
    return redirect(url_for('manage_users'))

@app.route('/admin/ratings')
def manage_ratings():
    sort_by = request.args.get('sort_by', 'oyun_adi')
    order = request.args.get('order', 'asc')
    allowed_sorts = ['oyun_adi', 'average_rating', 'rating_count']
    if sort_by not in allowed_sorts:
        sort_by = 'oyun_adi'
    if order not in ['asc', 'desc']:
        order = 'asc'
    conn = get_db_connection()
    query = f"SELECT id, oyun_adi, average_rating, rating_count FROM games ORDER BY {sort_by} {order}"
    games = conn.execute(query).fetchall()
    conn.close()
    next_order = 'desc' if order == 'asc' else 'asc'
    return render_template('manage_ratings.html', games=games, sort_by=sort_by, next_order=next_order)

@app.route('/admin/statistics')
def manage_statistics():
    sort_by = request.args.get('sort_by', 'click_count') 
    order = request.args.get('order', 'desc')
    allowed_sorts = ['oyun_adi', 'click_count']
    if sort_by not in allowed_sorts:
        sort_by = 'click_count'
    if order not in ['asc', 'desc']:
        order = 'desc'
    
    conn = get_db_connection()
    query = f"SELECT id, oyun_adi, click_count FROM games ORDER BY {sort_by} {order}"
    games = conn.execute(query).fetchall()
    conn.close()
    
    next_order = 'desc' if order == 'asc' else 'asc'
    return render_template('manage_statistics.html', games=games, sort_by=sort_by, next_order=next_order)

@app.route('/admin/statistics/reset_all', methods=['POST'])
def reset_all_clicks():
    conn = get_db_connection()
    conn.execute('UPDATE games SET click_count = 0')
    conn.commit()
    conn.close()
    return redirect(url_for('manage_statistics'))

@app.route('/admin/ratings/reset_all', methods=['POST'])
def reset_all_ratings():
    conn = get_db_connection()
    conn.execute('DELETE FROM user_ratings')
    conn.execute('UPDATE games SET average_rating = 0, rating_count = 0')
    conn.commit()
    conn.close()
    return redirect(url_for('manage_ratings'))

@app.route('/admin/download_games')
def download_games():
    return render_template('download_games.html')

@app.route('/admin/license_management')
def license_management():
    return render_template('license_management.html')

@app.route('/admin/settings', methods=['GET', 'POST'])
def general_settings():
    if request.method == 'POST':
        cafe_name = request.form['cafe_name']
        slogan = request.form['slogan']
        set_setting('cafe_name', cafe_name)
        set_setting('slogan', slogan)

        background_type = request.form['background_type']
        set_setting('background_type', background_type)

        set_setting('primary_color_start', request.form['primary_color_start'])
        set_setting('primary_color_end', request.form['primary_color_end'])

        opacity_factor = request.form.get('background_opacity_factor', '1.0')
        try:
            factor = max(0.1, min(1.0, float(opacity_factor)))
            set_setting('background_opacity_factor', f"{factor:.1f}")
        except ValueError:
            set_setting('background_opacity_factor', '1.0')
        
        if background_type == 'custom_bg' and 'custom_background_file' in request.files:
            file = request.files['custom_background_file']
            if file and file.filename != '':
                current_settings = get_all_settings()
                old_file = current_settings.get('background_file')
                if old_file:
                    try: os.remove(os.path.join(app.config['UPLOAD_FOLDER_BG'], old_file))
                    except OSError: pass

                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER_BG'], filename))
                set_setting('background_file', filename)
            elif 'current_background_file' in request.form:
                set_setting('background_file', request.form['current_background_file'])
            else:
                set_setting('background_type', 'default')
                set_setting('background_file', '')
        
        if background_type == 'default':
            current_settings = get_all_settings()
            old_file = current_settings.get('background_file')
            if old_file:
                try: os.remove(os.path.join(app.config['UPLOAD_FOLDER_BG'], old_file))
                except OSError: pass
            set_setting('background_file', '')

        return redirect(url_for('general_settings'))

    settings = get_all_settings()
    settings.setdefault('cafe_name', 'Zenka Internet Cafe')
    settings.setdefault('slogan', 'Hazırsan, oyun başlasın.')
    settings.setdefault('background_type', 'default')
    settings.setdefault('background_file', '')
    settings.setdefault('background_opacity_factor', '1.0')
    settings.setdefault('primary_color_start', '#667eea')
    settings.setdefault('primary_color_end', '#764ba2')
    
    return render_template('general_settings.html', settings=settings)

if __name__ == '__main__':
    init_db() 
    
    for folder_key in ['UPLOAD_FOLDER_COVERS', 'UPLOAD_FOLDER_GALLERY', 'SAVE_FOLDER', 'UPLOAD_FOLDER_BG', 'UPLOAD_FOLDER_100_SAVES']:
        folder_path = app.config.get(folder_key)
        if folder_path and not os.path.exists(folder_path):
            os.makedirs(folder_path)
            
    print("Sunucu http://127.0.0.1:5000 adresinde başlatılıyor...")
    app.run(debug=True, port=5000)