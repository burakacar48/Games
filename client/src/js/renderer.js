window.addEventListener('DOMContentLoaded', () => {
    const SERVER_URL = 'http://127.0.0.1:5000';
    let authToken = null;
    let currentUser = null;
    let allGames = [];
    let allCategories = ['Tümü'];
    let userRatings = {};
    let userFavorites = new Set();
    let userSaves = new Set(); 

    let appSettings = {};
    const body = document.body;
    
    // --- HTML Elementlerini Seç ---
    const gameListContainer = document.getElementById('game-list');
    const userSessionContainer = document.getElementById('user-session');
    const searchInput = document.getElementById('search-input');
    const statsBar = document.getElementById('stats-bar');
    const categoryListContainer = document.getElementById('category-list');
    
    // Modal Elementleri
    const loginModal = document.getElementById('login-modal');
    const loginForm = document.getElementById('login-form');
    const loginError = document.getElementById('login-error');
    const modalTitle = document.getElementById('modal-title');
    const modalButton = document.getElementById('modal-button');
    const modalSwitchToRegister = document.getElementById('to-register');
    const modalSwitchToLogin = document.getElementById('to-login');
    
    // Game Detail Modal Elementleri
    const gameDetailModal = document.getElementById('game-detail-modal');
    const detailTitle = document.getElementById('detail-title');
    const detailDescription = document.getElementById('detail-description');
    const detailMeta = document.getElementById('detail-meta');
    const mainMedia = document.getElementById('detail-main-media');
    const thumbnailStrip = document.getElementById('detail-thumbnail-strip');
    const detailPlayButton = document.getElementById('detail-play-button');
    const userRatingStars = document.getElementById('user-rating-stars');
    const userRatingInner = userRatingStars ? userRatingStars.querySelector('.stars-inner') : null; 
    const averageRatingSummary = document.getElementById('average-rating-summary');
    const favoriteButton = document.getElementById('favorite-button');
    // Benzer Oyunlar Elementleri
    const similarGamesSection = document.querySelector('.similar-games-section');
    const similarGamesGrid = document.getElementById('similar-games-grid');

    // --- Fonksiyonlar ---
    const updateUserUI = () => {
        if (authToken) {
            userSessionContainer.innerHTML = `
                <button id="saved-games-button" class="btn-saved-games">Kayıtlı Oyunlarım</button>
                <span class="user-info">👤 ${currentUser}</span>
                <button id="logout-button" class="btn-logout">Çıkış Yap</button>
            `;
            document.getElementById('logout-button').addEventListener('click', handleLogout);
            document.getElementById('saved-games-button').addEventListener('click', () => {
                document.querySelector('.category-chip.active')?.classList.remove('active');
                document.getElementById('saved-games-button').classList.add('active');
                filterGames('Kayıtlarım'); 
            });
        } else {
            userSessionContainer.innerHTML = `
                <button id="show-login-button" class="btn-login">Giriş Yap / Kayıt Ol</button>
            `;
            document.getElementById('show-login-button').addEventListener('click', openLoginModal);
        }
        renderCategories(); 
    };

    const renderGames = (gamesToRender) => {
        gameListContainer.innerHTML = '';
        if (!gamesToRender || gamesToRender.length === 0) {
            gameListContainer.innerHTML = '<p style="text-align: center; grid-column: 1 / -1; color: #b8b8d1;">Oyun bulunamadı.</p>';
            statsBar.innerHTML = '';
            return;
        }
        gamesToRender.forEach((game, index) => {
            const imageUrl = `${SERVER_URL}/static/images/covers/${game.cover_image}`;
            const card = document.createElement('div');
            card.className = 'game-card';
            card.dataset.gameId = game.id;
            card.style.animationDelay = `${index * 0.05}s`;
            card.innerHTML = `
                <img src="${imageUrl}" alt="${game.oyun_adi}" class="game-image">
                <div class="game-info">
                    <h3 class="game-title">${game.oyun_adi}</h3>
                </div>
            `;
            gameListContainer.appendChild(card);
        });
        statsBar.innerHTML = `
            <div class="stat-item">
                <div class="stat-value">${allGames.length}</div>
                <div class="stat-label">Toplam Oyun Sayısı</div>
            </div>
        `;
    };
    
    const renderSimilarGames = (similarGames) => {
        if (!similarGamesGrid) return;
        similarGamesGrid.innerHTML = '';
        
        if (similarGames && similarGames.length > 0) {
            similarGames.forEach(game => {
                const imageUrl = `${SERVER_URL}/static/images/covers/${game.cover_image}`;
                const card = document.createElement('div');
                card.className = 'similar-game-card';
                card.dataset.gameId = game.id;
                card.innerHTML = `
                    <img src="${imageUrl}" alt="${game.oyun_adi}">
                    <h4>${game.oyun_adi}</h4>
                `;
                card.addEventListener('click', (e) => {
                    e.stopPropagation(); 
                    closeGameDetail();
                    const gameDetails = allGames.find(g => g.id == game.id);
                    if(gameDetails) showGameDetail(gameDetails);
                });
                similarGamesGrid.appendChild(card);
            });
            if (similarGamesSection) similarGamesSection.classList.remove('hidden');
        } else {
            if (similarGamesSection) similarGamesSection.classList.add('hidden');
        }
    };

    const handleCategoryClick = (clickedChip) => {
        document.querySelector('.category-chip.active')?.classList.remove('active');
        document.getElementById('saved-games-button')?.classList.remove('active');
        
        clickedChip.classList.add('active');
        filterGames();
        
        window.scrollTo({
            top: document.querySelector('.search-bar').offsetTop - 20,
            behavior: 'smooth'
        });
    };

    const renderCategories = () => {
        categoryListContainer.innerHTML = '';
        
        const allChip = document.createElement('div');
        allChip.className = 'category-chip active';
        allChip.textContent = 'Tümü';
        allChip.dataset.category = 'Tümü';
        allChip.addEventListener('click', () => handleCategoryClick(allChip));
        categoryListContainer.appendChild(allChip);
        
        if (authToken) {
            const favChip = document.createElement('div');
            favChip.className = 'category-chip favorites';
            favChip.dataset.category = 'Favorilerim';
            favChip.innerHTML = `<svg class="favorite-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><path d="M47.6 300.4L228.3 469.1c7.5 7 17.4 10.9 27.7 10.9s20.2-3.9 27.7-10.9L464.4 300.4c30.4-28.3 47.6-68 47.6-109.5v-5.8c0-69.9-50.5-129.5-119.4-141C347 36.5 300.6 51.4 268 84L256 96 244 84c-32.6-32.6-79-47.5-124.6-39.9C50.5 55.6 0 115.2 0 185.1v5.8c0 41.5 17.2 81.2 47.6 109.5z"/></svg> <span>Favorilerim</span>`;
            favChip.addEventListener('click', () => handleCategoryClick(favChip));
            categoryListContainer.appendChild(favChip);
        }

        allCategories.slice(1).forEach(categoryName => {
            const chip = document.createElement('div');
            chip.className = 'category-chip';
            chip.textContent = categoryName;
            chip.dataset.category = categoryName;
            chip.addEventListener('click', () => handleCategoryClick(chip));
            categoryListContainer.appendChild(chip);
        });
    };

    const filterGames = (overrideCategory = null) => {
        const searchTerm = searchInput.value.toLowerCase();
        let activeCategory = overrideCategory;
        if (!activeCategory) {
            const activeChip = document.querySelector('.category-chip.active');
            if (activeChip) {
                activeCategory = activeChip.dataset.category;
            } else {
                activeCategory = 'Tümü';
            }
        }

        let filtered = allGames;
        
        if (activeCategory === 'Kayıtlarım') {
            filtered = filtered.filter(game => userSaves.has(game.id));
        } else if (activeCategory === 'Favorilerim') {
            if (!authToken) {
                alert("Favorilerinizi görmek için giriş yapmalısınız.");
                handleCategoryClick(document.querySelector('.category-chip[data-category="Tümü"]'));
                return;
            }
            filtered = filtered.filter(game => userFavorites.has(game.id));
        } else if (activeCategory !== 'Tümü') {
            filtered = filtered.filter(game => game.kategori === activeCategory);
        }

        if (searchTerm) {
            filtered = filtered.filter(game => 
                game.oyun_adi.toLowerCase().includes(searchTerm)
            );
        }
        renderGames(filtered);
    };

    const fetchGames = () => {
        fetch(`${SERVER_URL}/api/games`).then(res => res.json()).then(games => {
            allGames = games;
            const uniqueCategories = [...new Set(games.map(g => g.kategori).filter(Boolean))];
            allCategories = ['Tümü', ...uniqueCategories.sort()];
            renderCategories();
            filterGames();
        }).catch(err => {
            console.error(err);
            gameListContainer.innerHTML = `<p style="color: red; text-align: center; grid-column: 1 / -1;">Oyun listesi alınamadı.</p>`;
        });
    };
    
    const fetchSettings = () => {
        fetch(`${SERVER_URL}/api/settings`).then(res => {
            if (!res.ok) {
                throw new Error(`API hatası: ${res.status}`);
            }
            return res.json();
        }).then(settings => {
            appSettings = settings;
            
            document.title = settings.cafe_name || "Zenka Internet Cafe"; 
            
            const headerH1 = document.querySelector('.header h1');
            const headerP = document.querySelector('.header p');
            if(headerH1) headerH1.textContent = settings.cafe_name || "Zenka Internet Cafe";
            if(headerP) headerP.textContent = settings.slogan || "Hazırsan, oyun başlasın.";
            
            const startColor = settings.primary_color_start || '#667eea';
            const endColor = settings.primary_color_end || '#764ba2';
            
            body.style.setProperty('--theme-primary-start', startColor);
            body.style.setProperty('--theme-primary-end', endColor);
            
            const opacityFactor = parseFloat(settings.background_opacity_factor) || 1.0;

            if (settings.background_type === 'custom_bg' && settings.background_file) {
                const imageUrl = `${SERVER_URL}/static/images/backgrounds/${settings.background_file}`;
                body.classList.add('custom-background');
                body.style.setProperty('--custom-bg-image', `url(${imageUrl})`);
            } else {
                body.classList.remove('custom-background');
                body.style.removeProperty('--custom-bg-image'); 
            }
            
            body.style.setProperty('--custom-bg-factor', opacityFactor); 

        }).catch(err => {
            console.error("Ayarlar çekilemedi:", err);
            const headerH1 = document.querySelector('.header h1');
            const headerP = document.querySelector('.header p');
            if(headerH1) headerH1.textContent = "Zenka Internet Cafe";
            if(headerP) headerP.textContent = "Hazırsan, oyun başlasın.";
        });
    }
    
    const updateRatingDisplay = (game) => {
        const avgRating = game.average_rating ? game.average_rating.toFixed(1) : 'N/A';
        if (averageRatingSummary) {
            averageRatingSummary.textContent = `Ortalama Puan: ${avgRating} (${game.rating_count || 0} oy)`;
        }
        const userRating = userRatings[game.id] || 0;
        if (userRatingInner) {
            userRatingInner.style.width = `${(userRating / 5) * 100}%`;
        }
    };

    const updateFavoriteDisplay = (gameId) => {
        if (favoriteButton) {
            favoriteButton.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><path d="M47.6 300.4L228.3 469.1c7.5 7 17.4 10.9 27.7 10.9s20.2-3.9 27.7-10.9L464.4 300.4c30.4-28.3 47.6-68 47.6-109.5v-5.8c0-69.9-50.5-129.5-119.4-141C347 36.5 300.6 51.4 268 84L256 96 244 84c-32.6-32.6-79-47.5-124.6-39.9C50.5 55.6 0 115.2 0 185.1v5.8c0 41.5 17.2 81.2 47.6 109.5z"/></svg>`;
            if (userFavorites.has(gameId)) {
                favoriteButton.classList.add('is-favorite');
            } else {
                favoriteButton.classList.remove('is-favorite');
            }
        }
    };
    
    const showGameDetail = (game) => {
        detailTitle.textContent = game.oyun_adi;
        detailDescription.textContent = game.aciklama || "Açıklama yok.";
        
        detailMeta.innerHTML = `
            <div class="meta-item">
                <span class="meta-label"><i class="fas fa-tags"></i> Kategori:</span>
                <span>${game.kategori||'N/A'}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label"><i class="fas fa-calendar-alt"></i> Çıkış Yılı:</span>
                <span>${game.cikis_yili||'N/A'}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label"><i class="fas fa-shield-alt"></i> PEGI:</span>
                <span>${game.pegi||'N/A'}</span>
            </div>`;

        updateRatingDisplay(game);
        updateFavoriteDisplay(game.id);
        thumbnailStrip.innerHTML = ''; mainMedia.innerHTML = '';
        if (game.youtube_id) {
            const videoThumb = document.createElement('div');
            videoThumb.className = 'thumbnail-item active';
            videoThumb.innerHTML = `<div class="video-thumb" style="background-image: url(https://img.youtube.com/vi/${game.youtube_id}/mqdefault.jpg)"><svg viewBox="0 0 384 512"><path d="M73 39c-14.8-9.1-33.4-9.4-48.5-.9S0 62.6 0 80V432c0 17.4 9.4 33.4 24.5 41.9s33.7 8.1 48.5-.9L361 297c14.3-8.7 23-24.2 23-41s-8.7-32.2-23-41L73 39z"/></svg></div>`;
            mainMedia.innerHTML = `<iframe src="https://www.youtube.com/embed/${game.youtube_id}?autoplay=1" allow="autoplay; fullscreen"></iframe>`;
            videoThumb.addEventListener('click', () => {
                document.querySelector('.thumbnail-item.active')?.classList.remove('active');
                videoThumb.classList.add('active');
                mainMedia.innerHTML = `<iframe src="https://www.youtube.com/embed/${game.youtube_id}?autoplay=1" allow="autoplay; fullscreen"></iframe>`;
            });
            thumbnailStrip.appendChild(videoThumb);
        }
        if (game.galeri && game.galeri.length > 0) {
            game.galeri.forEach((imgFile, index) => {
                const imgThumb = document.createElement('div');
                imgThumb.className = 'thumbnail-item';
                const imgSrc = `${SERVER_URL}/static/images/gallery/${imgFile}`;
                imgThumb.innerHTML = `<img src="${imgSrc}">`;
                imgThumb.addEventListener('click', () => {
                    document.querySelector('.thumbnail-item.active')?.classList.remove('active');
                    imgThumb.classList.add('active');
                    mainMedia.innerHTML = `<img src="${imgSrc}">`;
                });
                thumbnailStrip.appendChild(imgThumb);
                if (!game.youtube_id && index === 0) { imgThumb.click(); }
            });
        }
        if (detailPlayButton) detailPlayButton.dataset.gameId = game.id;
        if (gameDetailModal) gameDetailModal.style.display = 'block';
        
        const similarGames = allGames.filter(g => 
            g.kategori === game.kategori && g.id !== game.id
        ).slice(0, 4); 
        renderSimilarGames(similarGames); 
    };

    const closeGameDetail = () => { 
        if (gameDetailModal) gameDetailModal.style.display = 'none'; 
        mainMedia.innerHTML = ''; 
        if (similarGamesSection) similarGamesSection.classList.add('hidden'); 
    };
    
    // DÜZENLENDİ: syncAndLaunch fonksiyonu async yapıldı
    const syncAndLaunch = async (game) => {
        try {
            // Tıklamayı kaydet ve sunucunun yanıt vermesini bekle
            await fetch(`${SERVER_URL}/api/games/${game.id}/click`, { method: 'POST' });
        } catch (err) {
            console.error(`Tıklama kaydedilemedi: ${err}`);
        } finally {
            // Her durumda oyunu başlat
            window.electronAPI.launchGame(game);
        }
    };

    const setModalMode = (mode) => {
        if (loginForm && loginError && modalTitle && modalButton && modalSwitchToRegister && modalSwitchToLogin) {
            loginForm.reset(); loginError.textContent = '';
            if (mode === 'login') {
                modalTitle.textContent = 'Giriş Yap'; modalButton.textContent = 'Giriş'; loginForm.dataset.mode = 'login';
                modalSwitchToRegister.classList.remove('hidden'); modalSwitchToLogin.classList.add('hidden');
            } else {
                modalTitle.textContent = 'Kayıt Ol'; modalButton.textContent = 'Kayıt Ol'; loginForm.dataset.mode = 'register';
                modalSwitchToRegister.classList.add('hidden'); modalSwitchToLogin.classList.remove('hidden');
            }
        }
    };
    const openLoginModal = () => { setModalMode('login'); if (loginModal) loginModal.style.display = 'block'; const usernameInput = document.getElementById('username'); if (usernameInput) usernameInput.focus(); };
    const closeLoginModal = () => { if (loginModal) loginModal.style.display = 'none'; };

    const handleLogin = (event) => {
        event.preventDefault();
        const mode = loginForm.dataset.mode;
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const endpoint = (mode === 'login') ? '/api/login' : '/api/register';
        fetch(SERVER_URL + endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) })
            .then(async response => { const data = await response.json(); if (!response.ok) { throw new Error(data.mesaj); } return data; })
            .then(data => {
                if (mode === 'login') {
                    authToken = data.token; currentUser = username;
                    closeLoginModal(); updateUserUI();
                    
                    const ratingsPromise = fetch(`${SERVER_URL}/api/user/ratings`, { headers: { 'Authorization': `Bearer ${authToken}` } }).then(res => res.json());
                    const favoritesPromise = fetch(`${SERVER_URL}/api/user/favorites`, { headers: { 'Authorization': `Bearer ${authToken}` } }).then(res => res.json());
                    const savesPromise = fetch(`${SERVER_URL}/api/user/saves`, { headers: { 'Authorization': `Bearer ${authToken}` } }).then(res => res.json());

                    Promise.all([ratingsPromise, favoritesPromise, savesPromise]).then(([ratings, favorites, saves]) => {
                        userRatings = ratings;
                        userFavorites = new Set(favorites);
                        userSaves = new Set(saves);
                        filterGames(); 
                    });

                } else {
                    if (loginError) loginError.textContent = data.mesaj;
                    setTimeout(() => setModalMode('login'), 2000);
                }
            })
            .catch(error => { if (loginError) loginError.textContent = error.message; });
    };

    const handleLogout = () => {
        authToken = null; currentUser = null; userRatings = {}; userFavorites.clear(); userSaves.clear();
        updateUserUI();
        filterGames();
    };

    // --- Olay Dinleyicileri ---
    
    if (searchInput) searchInput.addEventListener('input', () => filterGames());

    if (gameListContainer) {
        gameListContainer.addEventListener('click', (e) => {
            const card = e.target.closest('.game-card');
            if (card) { const game = allGames.find(g => g.id == card.dataset.gameId); if(game) showGameDetail(game); }
        });
    }

    if (detailPlayButton) {
        detailPlayButton.addEventListener('click', () => {
            const game = allGames.find(g => g.id == detailPlayButton.dataset.gameId);
            if(game) {
                closeGameDetail();
                syncAndLaunch(game);
            }
        });
    }

    if (loginForm) loginForm.addEventListener('submit', handleLogin);
    
    document.querySelectorAll('.close-button').forEach(btn => { 
        btn.addEventListener('click', () => { closeLoginModal(); closeGameDetail(); }); 
    });
    
    if (modalSwitchToRegister && modalSwitchToRegister.querySelector('a')) {
        modalSwitchToRegister.querySelector('a').addEventListener('click', (e) => { e.preventDefault(); setModalMode('register'); });
    }
    if (modalSwitchToLogin && modalSwitchToLogin.querySelector('a')) {
        modalSwitchToLogin.querySelector('a').addEventListener('click', (e) => { e.preventDefault(); setModalMode('login'); });
    }
    
    if (userRatingStars && userRatingInner) {
        userRatingStars.addEventListener('mousemove', e => {
            const rect = userRatingStars.getBoundingClientRect();
            const hoverWidth = e.clientX - rect.left;
            const rating = Math.max(0.5, Math.ceil((hoverWidth / rect.width) * 10) / 2);
            userRatingInner.style.width = `${(rating / 5) * 100}%`;
        });
        userRatingStars.addEventListener('mouseleave', () => {
            const gameId = detailPlayButton.dataset.gameId;
            if (gameId && allGames.length > 0) { const game = allGames.find(g => g.id == gameId); if (game) updateRatingDisplay(game); }
        });
        userRatingStars.addEventListener('click', async e => {
            if (!authToken) { alert("Puan vermek için giriş yapmalısınız."); openLoginModal(); return; }
            const gameId = detailPlayButton.dataset.gameId;
            const rect = userRatingStars.getBoundingClientRect();
            const clickWidth = e.clientX - rect.left;
            const rating = Math.max(0.5, Math.ceil((clickWidth / rect.width) * 10) / 2);
            try {
                const response = await fetch(`${SERVER_URL}/api/games/${gameId}/rate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                    body: JSON.stringify({ rating: rating })
                });
                const result = await response.json();
                if (!response.ok) throw new Error(result.mesaj);
                userRatings[gameId] = rating;
                const game = allGames.find(g => g.id == gameId);
                game.average_rating = result.average_rating;
                game.rating_count = result.rating_count;
                updateRatingDisplay(game);
                alert(`Puanınız (${rating}) başarıyla kaydedildi!`);
            } catch (error) {
                alert(`Puan kaydedilirken hata oluştu: ${error.message}`);
            }
        });
    }

    if (favoriteButton && detailPlayButton) {
        favoriteButton.addEventListener('click', async () => {
            if (!authToken) { alert("Favorilere eklemek için giriş yapmalısınız."); openLoginModal(); return; }
            const gameId = parseInt(detailPlayButton.dataset.gameId, 10);
            try {
                const response = await fetch(`${SERVER_URL}/api/games/${gameId}/favorite`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${authToken}` }
                });
                const result = await response.json();
                if (!response.ok) throw new Error(result.mesaj);
                if (result.is_favorite) { userFavorites.add(gameId); } 
                else { userFavorites.delete(gameId); }
                updateFavoriteDisplay(gameId);
                filterGames();
            } catch (error) {
                alert(`Bir hata oluştu: ${error.message}`);
            }
        });
    }

    window.addEventListener('click', (e) => { 
        if (e.target.classList.contains('modal')) { closeLoginModal(); closeGameDetail(); }
    });

    fetchSettings();
    fetchGames();
    updateUserUI(); 
});