import ApiClient from './api.js';

const api = new ApiClient('');

// DOM элементы
const messageContainer = document.getElementById('messageContainer');
const homeLink = document.getElementById('homeLink');
const adminLink = document.getElementById('adminLink');
const logoutButton = document.getElementById('logoutButton');

// Показать сообщение
function showMessage(message, type = 'info') {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    messageContainer.appendChild(alert);

    setTimeout(() => {
        alert.remove();
    }, 5000);
}

async function loadProfileData() {
    try {
        const data = await api.get('/api/v0/profile/data');

        document.getElementById('userId').textContent = data.id;
        document.getElementById('username').textContent = data.username;
        document.getElementById('email').textContent = data.email;
        document.getElementById('fullName').textContent = data.full_name || 'Не указано';
        document.getElementById('tokenType').textContent = data.token_type.toUpperCase();
        document.getElementById('createdAt').textContent = data.created_at
            ? new Date(data.created_at).toLocaleString('ru-RU')
            : '-';

        // Заполняем поля редактирования
        document.getElementById('editEmail').value = data.email;
        document.getElementById('editFullName').value = data.full_name || '';

        // Проверяем, является ли пользователь админом
        if (data.role === 'admin' || data.is_admin) {
            adminLink.style.display = 'inline-block';
        }

        return data;
    } catch (error) {
        console.error('Failed to load profile:', error);
        if (error.message?.includes('401')) {
            window.location.href = '/login?next=/api/v0/profile';
        } else {
            showMessage('Ошибка загрузки профиля: ' + error.message, 'error');
        }
    }
}

async function loadMyTokens() {
    try {
        const data = await api.get('/api/v0/profile/tokens');
        const tbody = document.getElementById('tokensList');

        if (!data.tokens || data.tokens.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">Нет активных токенов</td></tr>';
            return;
        }

        tbody.innerHTML = data.tokens.map(token => `
            <tr>
                <td>${token.token_type || 'opaque'}</td>
                <td><code>${token.client_id}</code></td>
                <td>${token.scope || '-'}</td>
                <td>${token.issued_at ? new Date(token.issued_at).toLocaleString('ru-RU') : '-'}</td>
                <td>${token.expires_at ? new Date(token.expires_at).toLocaleString('ru-RU') : '-'}</td>
                <td>
                    <button class="btn-danger btn-sm revoke-token-btn" data-token="${token.access_token}" data-type="access">Отозвать</button>
                </td>
            </tr>
        `).join('');

        // Прикрепляем обработчики для кнопок отзыва
        document.querySelectorAll('.revoke-token-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const token = btn.getAttribute('data-token');
                const type = btn.getAttribute('data-type');
                await revokeToken(token, type);
            });
        });

    } catch (error) {
        console.error('Failed to load tokens:', error);
        document.getElementById('tokensList').innerHTML = '<tr><td colspan="6" style="text-align: center;">Ошибка загрузки токенов</td></tr>';
    }
}

// Отозвать токен
async function revokeToken(token, tokenType) {
    if (!confirm('Вы уверены, что хотите отозвать этот токен?')) return;

    try {
        await api.post('/api/v0/profile/tokens/revoke', { token, token_type: tokenType });
        showMessage('Токен успешно отозван', 'success');
        loadMyTokens();
    } catch (error) {
        showMessage('Ошибка отзыва токена: ' + error.message, 'error');
    }
}

// Отозвать все токены
async function revokeAllTokens() {
    if (!confirm('Отозвать ВСЕ токены? Это может прервать активные сессии в других приложениях.')) return;

    try {
        await api.post('/api/v0/profile/tokens/revoke-all', {});
        showMessage('Все токены успешно отозваны', 'success');
        loadMyTokens();
    } catch (error) {
        showMessage('Ошибка отзыва токенов: ' + error.message, 'error');
    }
}

async function updateProfile(fullName) {
    try {
        await api.put('/api/v0/profile/data', { full_name: fullName });
        showMessage('Профиль успешно обновлён', 'success');
        loadProfileData();
        return true;
    } catch (error) {
        showMessage('Ошибка обновления профиля: ' + error.message, 'error');
        return false;
    }
}

async function changePassword(oldPassword, newPassword) {
    try {
        await api.put('/api/v0/profile/change-password', {
            old_password: oldPassword,
            new_password: newPassword
        });
        showMessage('Пароль успешно изменён. Пожалуйста, войдите снова.', 'success');
        setTimeout(() => {
            window.location.href = '/logout';
        }, 2000);
        return true;
    } catch (error) {
        showMessage('Ошибка смены пароля: ' + error.message, 'error');
        return false;
    }
}

// Выход
async function logout() {
    try {
        await api.post('/logout');
        window.location.href = '/login';
    } catch (error) {
        console.error('Logout error:', error);
        window.location.href = '/login';
    }
}

// Инициализация вкладок
function initTabs() {
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });

            const tabId = `tab-${tab.getAttribute('data-tab')}`;
            document.getElementById(tabId).classList.add('active');

            // Загружаем токены при переключении на вкладку токенов
            if (tab.getAttribute('data-tab') === 'tokens') {
                loadMyTokens();
            }
        });
    });
}

// Инициализация событий
function initEvents() {
    // Редактирование профиля
    const editBtn = document.getElementById('editProfileBtn');
    const cancelBtn = document.getElementById('cancelEditBtn');
    const profileView = document.getElementById('profileView');
    const profileEdit = document.getElementById('profileEdit');
    const editForm = document.getElementById('profileEditForm');

    if (editBtn) {
        editBtn.addEventListener('click', () => {
            profileView.style.display = 'none';
            profileEdit.style.display = 'block';
        });
    }

    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            profileView.style.display = 'block';
            profileEdit.style.display = 'none';
        });
    }

    if (editForm) {
        editForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fullName = document.getElementById('editFullName').value;

            const success = await updateProfile(fullName);
            if (success) {
                profileView.style.display = 'block';
                profileEdit.style.display = 'none';
            }
        });
    }

    // Смена пароля
    const passwordForm = document.getElementById('changePasswordForm');
    if (passwordForm) {
        passwordForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const oldPassword = document.getElementById('oldPassword').value;
            const newPassword = document.getElementById('newPassword').value;
            const confirmPassword = document.getElementById('confirmPassword').value;

            if (newPassword !== confirmPassword) {
                showMessage('Новый пароль и подтверждение не совпадают', 'error');
                return;
            }

            if (newPassword.length < 8) {
                showMessage('Пароль должен содержать минимум 8 символов', 'error');
                return;
            }

            await changePassword(oldPassword, newPassword);
            passwordForm.reset();
        });
    }

    // Отзыв всех токенов
    const revokeAllBtn = document.getElementById('revokeAllTokensBtn');
    if (revokeAllBtn) {
        revokeAllBtn.addEventListener('click', revokeAllTokens);
    }

    // Выход
    if (logoutButton) {
        logoutButton.addEventListener('click', logout);
    }
}

// Инициализация
async function init() {
    initTabs();
    initEvents();
    await loadProfileData();
}

init();