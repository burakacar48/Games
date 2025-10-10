window.addEventListener('DOMContentLoaded', () => {
    const SERVER_URL = 'http://127.0.0.1:5000';
    let authToken = null;
    let currentUser = null;
    let allGames = [];
    let allCategories = [];
    let userRatings = {};
    let userFavorites = new Set();
    let userSaves = new Set();
    let currentFilter = 'all';
    let sliderInterval;

    // === Arayüz Elementleri ===
    const gamesGrid = document.getElementById('gamesGrid');
    const searchInput = document.getElementById('searchInput');
    const sectionTitle = document.getElementById('sectionTitle');
    const userActions = document.getElementById('user-actions');
    const categoryListSidebar = document.getElementById('category-list-sidebar');
    const heroSection = document.getElementById('hero-section');


    // === Giriş Modal Elementleri ===
    const loginModal = document.getElementById('login-modal');
    const loginForm = document.getElementById('login-form');
    const loginError = document.getElementById('login-error');
    const modalTitle = document.getElementById('modal-title');
    const modalButton = document.getElementById('modal-button');
    const modalSwitchToRegister = document.getElementById('to-register');
    const modalSwitchToLogin = document.getElementById('to-login');
    
    // === OYUN DETAY MODAL ELEMENTLERİ ===
    const gameDetailModal = document.getElementById('game-detail-modal');
    const detailTitle = document.getElementById('detail-title');
    const detailDescription = document.getElementById('detail-description');
    const detailMeta = document.getElementById('detail-meta');
    const mainMedia = document.getElementById('detail-main-media');
    const thumbnailStrip = document.getElementById('detail-thumbnail-strip');
    const playButtonArea = document.getElementById('play-button-area');
    const userRatingStars = document.getElementById('user-rating-stars');
    const userRatingInner = userRatingStars ? userRatingStars.querySelector('.stars-inner') : null;
    const averageRatingSummary = document.getElementById('average-rating-summary');
    const favoriteButton = document.getElementById('favorite-button');
    const similarGamesSection = document.querySelector('.similar-games-section');
    const similarGamesGrid = document.getElementById('similar-games-grid');

    // === AYARLARI ÇEK VE UYGULA ===
    const fetchAndApplySettings = () => {
        fetch(`${SERVER_URL}/api/settings`)
            .then(res => res.json())
            .then(settings => {
                console.log('Ayarlar sunucudan alındı:', settings);
                const root = document.documentElement;
                if (settings.primary_color_start && settings.primary_color_end) {
                    root.style.setProperty('--primary-start', settings.primary_color_start);
                    root.style.setProperty('--primary-end', settings.primary_color_end);
                }

                const logoImageContainer = document.getElementById('logo-image-container');
                const cafeLogo = document.getElementById('cafe-logo');
                const cafeTagline = document.getElementById('cafe-tagline');

                if (cafeTagline) cafeTagline.innerText = settings.slogan || '';

                if (settings.logo_file) {
                    logoImageContainer.innerHTML = `<img src="${SERVER_URL}/static/images/logos/${settings.logo_file}" alt="Kafe Logosu">`;
                    logoImageContainer.classList.remove('hidden');
                    cafeLogo.classList.add('hidden');
                } else {
                    if (cafeLogo) cafeLogo.innerText = settings.cafe_name || 'Kafe Adı';
                    logoImageContainer.classList.add('hidden');
                    cafeLogo.classList.remove('hidden');
                }
            })
            .catch(error => console.error('Ayarlar çekilirken hata oluştu:', error));
    };


    const renderGames = (filter = 'all', searchTerm = '') => {
        let filtered = allGames;

        if (filter !== 'all' && filter !== 'favorites' && filter !== 'recent') {
            filtered = allGames.filter(g => g.kategori === filter);
        } else if (filter === 'favorites') {
             if (!authToken) {
                alert("Favorilerinizi görmek için giriş yapmalısınız.");
                document.querySelector('.nav-item[data-category="all"]').click();
                return;
            }
            filtered = allGames.filter(g => userFavorites.has(g.id));
        }

        if (searchTerm) {
            filtered = filtered.filter(g => g.oyun_adi.toLowerCase().includes(searchTerm.toLowerCase()));
        }

        gamesGrid.innerHTML = '';
        if (filtered.length > 0) {
            filtered.forEach(game => {
                const gameCard = `
                    <div class="game-card" data-game-id="${game.id}">
                        <div class="game-image-wrapper">
                            <img src="${SERVER_URL}/static/images/covers/${game.cover_image}" alt="${game.oyun_adi}" class="game-image" onerror="this.src='https://via.placeholder.com/400x500/1a1a1a/ef4444?text=${encodeURIComponent(game.oyun_adi)}'">
                            <div class="game-overlay">
                                <div class="play-btn">ℹ️</div>
                            </div>
                        </div>
                        <div class="game-info">
                            <div class="game-title">${game.oyun_adi}</div>
                            <div class="game-category">${game.kategori || 'Kategorisiz'}</div>
                        </div>
                    </div>
                `;
                gamesGrid.innerHTML += gameCard;
            });
        } else {
            gamesGrid.innerHTML = '<p style="color: #aaa; grid-column: 1 / -1; text-align: center;">Bu kategoride oyun bulunamadı.</p>';
        }
        updateSectionTitle(filter);
    };
    
    const showGameDetail = (game) => {
        detailTitle.textContent = game.oyun_adi;
        detailDescription.textContent = game.aciklama || "Açıklama bulunmuyor.";
        
        detailMeta.innerHTML = `
            <div class="meta-item">
                <span><i class="fas fa-tags"></i> Kategori:</span>
                <span>${game.kategori||'N/A'}</span>
            </div>
            <div class="meta-item">
                <span><i class="fas fa-calendar-alt"></i> Çıkış Yılı:</span>
                <span>${game.cikis_yili||'N/A'}</span>
            </div>
            <div class="meta-item">
                <span><i class="fas fa-shield-alt"></i> PEGI:</span>
                <span>${game.pegi||'N/A'}</span>
            </div>`;

        updateRatingDisplay(game);
        updateFavoriteDisplay(game.id);
        thumbnailStrip.innerHTML = '';
        mainMedia.innerHTML = '';
        
        if (game.youtube_id) {
            const videoThumb = document.createElement('div');
            videoThumb.className = 'thumbnail-item active';
            videoThumb.innerHTML = `<div class="video-thumb" style="background-image: url(https://img.youtube.com/vi/${game.youtube_id}/mqdefault.jpg)"><i class="fas fa-play"></i></div>`;
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
                if (!game.youtube_id && index === 0) {
                    imgThumb.click();
                }
            });
        }
        
        playButtonArea.innerHTML = '';
        playButtonArea.style.flexDirection = 'column';

        const playButton = document.createElement('button');
        playButton.className = 'hero-btn primary';
        playButton.innerHTML = '▶ Şimdi Oyna';
        playButton.dataset.gameId = game.id;
        playButton.addEventListener('click', () => {
            closeGameDetail();
            syncAndLaunch(game);
        });
        
        if (game.kategori !== 'Online Oyunlar' && game.yuzde_yuz_save_path) {
            playButtonArea.style.flexDirection = 'row';
            const saveButton = document.createElement('button');
            saveButton.className = 'hero-btn secondary';
            saveButton.textContent = '%100 SAVE';
            saveButton.addEventListener('click', () => {
                handle100Save(game.id, game.save_yolu);
            });
            playButtonArea.appendChild(saveButton);
        }

        playButtonArea.appendChild(playButton);

        if (gameDetailModal) gameDetailModal.style.display = 'flex';
        
        const similarGames = allGames.filter(g => g.kategori === game.kategori && g.id !== game.id).slice(0, 5);
        renderSimilarGames(similarGames);
    };

    const closeGameDetail = () => {
        if (gameDetailModal) gameDetailModal.style.display = 'none';
        mainMedia.innerHTML = '';
        if (similarGamesSection) similarGamesSection.classList.add('hidden');
    };

    const renderSimilarGames = (similarGames) => {
        if (!similarGamesGrid) return;
        similarGamesGrid.innerHTML = '';

        if (similarGames && similarGames.length > 0) {
            similarGames.forEach(game => {
                const card = `
                <div class="game-card similar" data-game-id="${game.id}">
                    <div class="game-image-wrapper">
                        <img src="${SERVER_URL}/static/images/covers/${game.cover_image}" alt="${game.oyun_adi}" class="game-image">
                    </div>
                    <div class="game-info">
                        <div class="game-title">${game.oyun_adi}</div>
                    </div>
                </div>`;
                similarGamesGrid.innerHTML += card;
            });
            if (similarGamesSection) similarGamesSection.classList.remove('hidden');
        } else {
            if (similarGamesSection) similarGamesSection.classList.add('hidden');
        }
    };
    
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
            favoriteButton.innerHTML = `<i class="fas fa-heart"></i>`;
            if (userFavorites.has(gameId)) {
                favoriteButton.classList.add('is-favorite');
            } else {
                favoriteButton.classList.remove('is-favorite');
            }
        }
    };

    const updateSectionTitle = (filter) => {
        const titles = {
            'all': 'Tüm Oyunlar',
            'favorites': 'Favori Oyunlarım',
            'recent': 'Son Oynanan Oyunlar',
        };
        sectionTitle.textContent = titles[filter] || `${filter} Oyunları`;
    };

    const fetchGameAndCategories = () => {
        Promise.all([
            fetch(`${SERVER_URL}/api/games`).then(res => res.json()),
            fetch(`${SERVER_URL}/api/categories`).then(res => res.json())
        ]).then(([games, categories]) => {
            allGames = games;
            allCategories = categories;
            renderCategories();
            renderGames();
            updateHeroSection();
        }).catch(error => console.error('Veri çekme hatası:', error));
    };
    
    const updateHeroSection = () => {
        fetch(`${SERVER_URL}/api/slider`)
            .then(res => res.json())
            .then(sliders => {
                if (!sliders || sliders.length === 0) {
                    heroSection.style.display = 'none';
                    return;
                }

                heroSection.innerHTML = ''; // Önceki içeriği temizle
                heroSection.style.display = 'block';

                sliders.forEach((slide, index) => {
                    const slideElement = document.createElement('div');
                    slideElement.className = 'hero-slide';
                    if (index === 0) slideElement.classList.add('active');

                    slideElement.innerHTML = `
                        <img src="${SERVER_URL}/static/images/slider/${slide.background_image}" class="hero-bg" alt="Featured">
                        <div class="hero-overlay"></div>
                        <div class="hero-content">
                            <div class="hero-badge">${slide.badge_text}</div>
                            <h1 class="hero-title">${slide.title}</h1>
                            <p class="hero-description">${slide.description}</p>
                            <div class="hero-actions">
                                <button class="hero-btn primary" data-game-id="${slide.game_id}">▶ Şimdi Oyna</button>
                                <button class="hero-btn secondary" data-game-id="${slide.game_id}">ℹ️ Detaylar</button>
                            </div>
                        </div>
                    `;
                    heroSection.appendChild(slideElement);
                });

                // Butonlara event listener ekle
                document.querySelectorAll('.hero-btn').forEach(button => {
                    button.addEventListener('click', function() {
                        const gameId = this.dataset.gameId;
                        const game = allGames.find(g => g.id == gameId);
                        if (game) {
                            if (this.classList.contains('primary')) {
                                syncAndLaunch(game);
                            } else {
                                showGameDetail(game);
                            }
                        }
                    });
                });
                
                // Slider'ı başlat
                startSlider(sliders.length);
            })
            .catch(error => {
                console.error('Slider verisi alınırken hata:', error);
                heroSection.style.display = 'none';
            });
    };

    function startSlider(slideCount) {
        if (slideCount <= 1) return;
        let currentSlide = 0;
        const slides = document.querySelectorAll('.hero-slide');

        clearInterval(sliderInterval); 

        sliderInterval = setInterval(() => {
            slides[currentSlide].classList.remove('active');
            currentSlide = (currentSlide + 1) % slideCount;
            slides[currentSlide].classList.add('active');
        }, 7000); // 7 saniyede bir geçiş
    }


    const renderCategories = () => {
        categoryListSidebar.innerHTML = '';
        allCategories.forEach(category => {
            const navItem = document.createElement('div');
            navItem.className = 'nav-item';
            navItem.dataset.category = category.name;
            const icon = category.icon || '🎮';
            navItem.innerHTML = `<span class="nav-icon">${icon}</span> ${category.name}`;
            categoryListSidebar.appendChild(navItem);
        });
        addCategoryEventListeners();
    };

    const addCategoryEventListeners = () => {
        document.querySelectorAll('.nav-item[data-category]').forEach(item => {
            item.addEventListener('click', function() {
                document.querySelectorAll('.nav-item.active').forEach(i => i.classList.remove('active'));
                this.classList.add('active');
                currentFilter = this.dataset.category;
                renderGames(currentFilter, searchInput.value);
            });
        });
    };

    const updateUserUI = () => {
        if (authToken) {
            userActions.innerHTML = `
                <button class="action-btn">Kayıtlı Oyunlar</button>
                <button class="action-btn primary" id="logout-button">Çıkış Yap</button>
            `;
            document.getElementById('logout-button').addEventListener('click', handleLogout);
        } else {
            userActions.innerHTML = `
                <button class="action-btn primary" id="login-show-button">Giriş Yap / Kayıt ol</button>
            `;
            document.getElementById('login-show-button').addEventListener('click', openLoginModal);
        }
    };
    
    const handleLogout = () => {
        authToken = null;
        currentUser = null;
        userFavorites.clear();
        updateUserUI();
        if (currentFilter === 'favorites') {
            document.querySelector('.nav-item[data-category="all"]').click();
        } else {
            renderGames(currentFilter, searchInput.value);
        }
    };
    
    const openLoginModal = () => {
        setModalMode('login');
        if (loginModal) loginModal.style.display = 'flex';
        const usernameInput = document.getElementById('username');
        if (usernameInput) usernameInput.focus();
    };

    const closeLoginModal = () => {
        if (loginModal) loginModal.style.display = 'none';
    };
    
    const setModalMode = (mode) => {
        if (loginForm && loginError && modalTitle && modalButton && modalSwitchToRegister && modalSwitchToLogin) {
            loginForm.reset();
            loginError.textContent = '';
            if (mode === 'login') {
                modalTitle.textContent = 'Giriş Yap';
                modalButton.textContent = 'Giriş';
                loginForm.dataset.mode = 'login';
                modalSwitchToRegister.classList.remove('hidden');
                modalSwitchToLogin.classList.add('hidden');
            } else {
                modalTitle.textContent = 'Kayıt Ol';
                modalButton.textContent = 'Kayıt Ol';
                loginForm.dataset.mode = 'register';
                modalSwitchToRegister.classList.add('hidden');
                modalSwitchToLogin.classList.remove('hidden');
            }
        }
    };
    
    const handleLogin = (event) => {
        event.preventDefault();
        const mode = loginForm.dataset.mode;
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const endpoint = (mode === 'login') ? '/api/login' : '/api/register';

        fetch(SERVER_URL + endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            })
            .then(async response => {
                const data = await response.json();
                if (!response.ok) throw new Error(data.mesaj);
                return data;
            })
            .then(data => {
                if (mode === 'login') {
                    authToken = data.token;
                    currentUser = username;
                    closeLoginModal();
                    updateUserUI();
                    fetchUserSpecificData();
                } else {
                    if (loginError) loginError.textContent = data.mesaj;
                    setTimeout(() => setModalMode('login'), 2000);
                }
            })
            .catch(error => {
                if (loginError) loginError.textContent = error.message;
            });
    };
    
    const fetchUserSpecificData = () => {
        if (!authToken) return;
        const headers = { 'Authorization': `Bearer ${authToken}` };
        Promise.all([
            fetch(`${SERVER_URL}/api/user/favorites`, { headers }).then(res => res.json()),
            fetch(`${SERVER_URL}/api/user/ratings`, { headers }).then(res => res.json())
        ]).then(([favorites, ratings]) => {
            userFavorites = new Set(favorites);
            userRatings = ratings;
            renderGames(currentFilter, searchInput.value);
        });
    };
    
    const syncAndLaunch = async (game) => {
        try {
            await fetch(`${SERVER_URL}/api/games/${game.id}/click`, { method: 'POST' });
        } catch (err) {
            console.error(`Tıklama kaydedilemedi: ${err}`);
        } finally {
            window.electronAPI.launchGame(game);
        }
    };

    searchInput.addEventListener('input', (e) => {
        renderGames(currentFilter, e.target.value);
    });
    
    gamesGrid.addEventListener('click', (e) => {
        const card = e.target.closest('.game-card');
        if (card) {
            const gameId = card.dataset.gameId;
            const game = allGames.find(g => g.id == gameId);
            if (game) {
                showGameDetail(game);
            }
        }
    });

    similarGamesGrid.addEventListener('click', (e) => {
        const card = e.target.closest('.game-card.similar');
        if(card){
            const gameId = card.dataset.gameId;
            const game = allGames.find(g => g.id == gameId);
            if(game) {
                closeGameDetail();
                setTimeout(() => showGameDetail(game), 100);
            }
        }
    });

    document.querySelectorAll('.close-button').forEach(btn => {
        btn.addEventListener('click', () => {
            closeLoginModal();
            closeGameDetail();
        });
    });
    
    modalSwitchToRegister.querySelector('a').addEventListener('click', (e) => { e.preventDefault(); setModalMode('register'); });
    modalSwitchToLogin.querySelector('a').addEventListener('click', (e) => { e.preventDefault(); setModalMode('login'); });
    loginForm.addEventListener('submit', handleLogin);
    
    if (userRatingStars && userRatingInner) {
        userRatingStars.addEventListener('mousemove', e => {
            if (!authToken) return;
            const rect = userRatingStars.getBoundingClientRect();
            const hoverWidth = e.clientX - rect.left;
            const rating = Math.max(0.5, Math.ceil((hoverWidth / rect.width) * 10) / 2);
            userRatingInner.style.width = `${(rating / 5) * 100}%`;
        });

        userRatingStars.addEventListener('mouseleave', () => {
            const gameId = playButtonArea.querySelector('.hero-btn.primary')?.dataset.gameId;
            if (gameId && allGames.length > 0) { const game = allGames.find(g => g.id == gameId); if (game) updateRatingDisplay(game); }
        });

        userRatingStars.addEventListener('click', async e => {
            if (!authToken) {
                closeGameDetail();
                openLoginModal();
                return;
            }
            const gameId = playButtonArea.querySelector('.hero-btn.primary')?.dataset.gameId;
            if(!gameId) return;

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
                console.log(`Puanınız (${rating}) başarıyla kaydedildi!`);
            } catch (error) {
                console.error(`Puan kaydedilirken hata oluştu: ${error.message}`);
            }
        });
    }

    if (favoriteButton) {
        favoriteButton.addEventListener('click', async () => {
            if (!authToken) {
                closeGameDetail();
                openLoginModal();
                return;
            }
            const gameId = parseInt(playButtonArea.querySelector('.hero-btn.primary')?.dataset.gameId, 10);
            if(!gameId) return;
            
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
            } catch (error) {
                console.error(`Bir hata oluştu: ${error.message}`);
            }
        });
    }

    window.addEventListener('click', (e) => {
        if (e.target == loginModal || e.target == gameDetailModal) {
            closeLoginModal();
            closeGameDetail();
        }
    });

    fetchAndApplySettings();
    fetchGameAndCategories();
    updateUserUI();
});

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('active');
}