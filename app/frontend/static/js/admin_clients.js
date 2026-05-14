import ApiClient from './api.js';

const api = new ApiClient('');

// --- Вспомогательные функции ---
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), duration);
}

function showCustomConfirm(message, onConfirm, targetElement) {
    const existing = document.querySelector('.confirm-popup');
    if (existing) existing.remove();

    const rect = targetElement.getBoundingClientRect();
    const popup = document.createElement('div');
    popup.className = 'confirm-popup';
    popup.style.top = `${rect.bottom + window.scrollY + 5}px`;
    popup.style.left = `${rect.left + window.scrollX}px`;
    popup.innerHTML = `
        <p>${message}</p>
        <div class="confirm-buttons">
            <button class="btn-secondary" id="confirm-no">Нет</button>
            <button id="confirm-yes">Да</button>
        </div>
    `;
    document.body.appendChild(popup);

    const handleYes = () => { popup.remove(); onConfirm(); };
    const handleNo = () => popup.remove();

    popup.querySelector('#confirm-yes').addEventListener('click', handleYes);
    popup.querySelector('#confirm-no').addEventListener('click', handleNo);

    const outsideClick = (e) => {
        if (!popup.contains(e.target)) {
            popup.remove();
            document.removeEventListener('click', outsideClick);
        }
    };
    setTimeout(() => document.addEventListener('click', outsideClick), 0);
}

// --- API вызовы ---
async function apiCall(endpoint, method, data = null, headers = {}, content = true) {
    try {
        let result;
        if (data) {
            result = await api.request(method, endpoint, data, headers, content);
        } else {
            result = await api.request(method, endpoint, data, headers, content);
        }
        if (result && result.detail) throw new Error(result.detail);
        return result;
    } catch (err) {
        showToast(err.message || 'Ошибка запроса', 'error');
        throw err;
    }
}

async function logout() {
    try {
        await apiCall('/api/v0/users/logout', 'POST');
        window.location.href = '/login';
    } catch (err) {
        showToast('Ошибка выхода: ' + err.message, 'error');
    }
}

// --- Клиенты ---
async function loadClients() {
    try {
        const clients = await apiCall('/api/v0/admin/clients/list', 'GET');
        const tbody = document.getElementById('clientsList');
        if (!clients.length) {
            tbody.innerHTML = '<tr><td colspan="5">Нет созданных клиентов</td></tr>';
            return;
        }
        tbody.innerHTML = clients.map(c => `
            <tr>
                <td>${c.id}</td>
                <td>${c.application_name || '-'}</td>
                <td><code>${c.client_id}</code></td>
                <td><small>${c.redirect_uris || '-'}</small></td>
                <td class="actions">
                    <button class="btn-secondary" data-client-id="${c.id}" data-client-secret="${c.client_secret}" data-action="showSecret">Показать секрет</button>
                    <button class="btn-danger" data-client-id="${c.id}" data-action="deleteClient">Удалить</button>
                </td>
            </tr>
        `).join('');
        attachClientHandlers();
    } catch (e) {
        document.getElementById('clientsList').innerHTML = `<tr><td colspan="5">Ошибка: ${e.message}</td></tr>`;
    }
}

function attachClientHandlers() {
    document.querySelectorAll('[data-action="showSecret"]').forEach(btn => {
        btn.removeEventListener('click', handleShowSecret);
        btn.addEventListener('click', handleShowSecret);
    });
    document.querySelectorAll('[data-action="deleteClient"]').forEach(btn => {
        btn.removeEventListener('click', handleDeleteClient);
        btn.addEventListener('click', handleDeleteClient);
    });
}

function handleShowSecret(event) {
    const btn = event.currentTarget;
    const clientId = btn.getAttribute('data-client-id');
    const clientSecret = btn.getAttribute('data-client-secret');
    showToast(`Client ID: ${clientId}\nClient Secret: ${clientSecret}`, 'info', 5000);
}

function handleDeleteClient(event) {
    const btn = event.currentTarget;
    const clientId = btn.getAttribute('data-client-id');
    showCustomConfirm('Удалить клиента? Все связанные токены будут потеряны.', async () => {
        try {
            await apiCall(`/api/v0/admin/clients/${clientId}`, 'DELETE', null, {}, null);
            showToast('Клиент удалён', 'success');
            loadClients();
        } catch (err) {
            showToast(err.message, 'error');
        }
    }, btn);
}

async function createClientFromModal() {
    const name = document.getElementById('modalClientName').value.trim();
    const redirectUris = document.getElementById('modalClientRedirectUris').value.trim();

    if (!name || !redirectUris) {
        showToast('Заполните все поля', 'error');
        return;
    }

    try {
        const result = await apiCall('/api/v0/admin/clients', 'POST', { name, redirect_uris: redirectUris });
        showToast(`Клиент создан!\nClient ID: ${result.client_id}\nClient Secret: ${result.client_secret}\nСохраните секрет!`, 'success', 6000);
        document.getElementById('createClientModal').style.display = 'none';
        document.getElementById('modalClientName').value = '';
        document.getElementById('modalClientRedirectUris').value = '';
        loadClients();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// --- Пользователи ---
async function loadUsers() {
    try {
        const users = await apiCall('/api/v0/admin/users/list', 'GET');
        const tbody = document.getElementById('usersList');
        if (!users.length) {
            tbody.innerHTML = '<tr><td colspan="6">Нет пользователей</td></tr>';
            return;
        }
        tbody.innerHTML = users.map(u => `
            <tr>
                <td>${u.id}</td>
                <td>${u.username}</td>
                <td>${u.email}</td>
                <td>${u.full_name || '-'}</td>
                <td>${u.is_active ? 'Да' : 'Нет'}</td>
                <td class="actions">
                    <button class="btn-secondary" data-user-id="${u.id}" data-user-email="${u.email.replace(/"/g, '&quot;')}" data-user-fullname="${u.full_name || ''}" data-user-active="${u.is_active}" data-action="editUser">Редактировать</button>
                    <button class="btn-danger" data-user-id="${u.id}" data-action="deleteUser">Удалить</button>
                </td>
            </tr>
        `).join('');
        attachUserHandlers();
        populateUserSelect(users);
    } catch (e) {
        document.getElementById('usersList').innerHTML = `<tr><td colspan="6">Ошибка: ${e.message}</td></tr>`;
    }
}

function populateUserSelect(users) {
    const select = document.getElementById('tokenUserSelect');
    if (!select) return;
    const currentVal = select.value;
    select.innerHTML = '<option value="">-- Выберите пользователя --</option>' +
        users.map(u => `<option value="${u.id}">${u.username} (${u.id})</option>`).join('');
    if (currentVal && users.some(u => u.id == currentVal)) {
        select.value = currentVal;
        loadTokensForUser(parseInt(currentVal));
    }
}

function attachUserHandlers() {
    document.querySelectorAll('[data-action="editUser"]').forEach(btn => {
        btn.removeEventListener('click', handleEditUser);
        btn.addEventListener('click', handleEditUser);
    });
    document.querySelectorAll('[data-action="deleteUser"]').forEach(btn => {
        btn.removeEventListener('click', handleDeleteUser);
        btn.addEventListener('click', handleDeleteUser);
    });
}

function handleEditUser(event) {
    const btn = event.currentTarget;
    const id = btn.getAttribute('data-user-id');
    const email = btn.getAttribute('data-user-email');
    const fullName = btn.getAttribute('data-user-fullname');
    const isActive = btn.getAttribute('data-user-active') === 'true';

    document.getElementById('editUserId').value = id;
    document.getElementById('editUserEmail').value = email;
    document.getElementById('editUserFullName').value = fullName;
    document.getElementById('editUserIsActive').checked = isActive;
    document.getElementById('editUserPassword').value = '';
    document.getElementById('editUserModal').style.display = 'flex';
}

function handleDeleteUser(event) {
    const btn = event.currentTarget;
    const userId = btn.getAttribute('data-user-id');
    showCustomConfirm('Удалить пользователя? Все его токены будут потеряны.', async () => {
        try {
            await apiCall(`/api/v0/admin/users/${userId}`, 'DELETE');
            showToast('Пользователь удалён', 'success');
            loadUsers();
            const select = document.getElementById('tokenUserSelect');
            if (select.value == userId) {
                select.value = '';
                document.getElementById('tokensList').innerHTML = '<tr><td colspan="8">Выберите пользователя</td></tr>';
            }
        } catch (err) {
            showToast(err.message, 'error');
        }
    }, btn);
}

async function updateUser(id, email, full_name, password, is_active) {
    const payload = { email, full_name, is_active };
    if (password) payload.password = password;
    try {
        await apiCall(`/api/v0/admin/users/${id}`, 'PUT', payload);
        showToast('Пользователь обновлён', 'success');
        document.getElementById('editUserModal').style.display = 'none';
        loadUsers();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function createUserFromModal() {
    const username = document.getElementById('modalUserUsername').value.trim();
    const email = document.getElementById('modalUserEmail').value.trim();
    const full_name = document.getElementById('modalUserFullName').value.trim();
    const password = document.getElementById('modalUserPassword').value;
    const is_active = document.getElementById('modalUserIsActive').checked;

    if (!username || !email || !password) {
        showToast('Заполните обязательные поля: Username, Email, Пароль', 'error');
        return;
    }

    try {
        await apiCall('/api/v0/admin/users', 'POST', { username, email, full_name, password, is_active });
        showToast('Пользователь создан', 'success');
        document.getElementById('createUserModal').style.display = 'none';
        document.getElementById('modalUserUsername').value = '';
        document.getElementById('modalUserEmail').value = '';
        document.getElementById('modalUserFullName').value = '';
        document.getElementById('modalUserPassword').value = '';
        document.getElementById('modalUserIsActive').checked = true;
        loadUsers();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// --- Токены выбранного пользователя ---
let currentUserId = null;

async function loadTokensForUser(userId) {
    if (!userId) {
        document.getElementById('tokensList').innerHTML = '<tr><td colspan="8">Выберите пользователя</td></tr>';
        return;
    }
    currentUserId = userId;
    try {
        const tokens = await apiCall(`/api/v0/admin/users/${userId}/tokens`, 'GET');
        const tbody = document.getElementById('tokensList');
        if (!tokens.length) {
            tbody.innerHTML = '<tr><td colspan="8">Нет активных токенов</td></tr>';
            return;
        }
        tbody.innerHTML = tokens.map(t => `
            <tr>
                <td>${t.token_type || 'opaque'}</td>
                <td><code>${t.client_id}</code></td>
                <td>${t.scope || '-'}</td>
                <td>${t.issued_at ? new Date(t.issued_at).toLocaleString() : '-'}</td>
                <td>${t.expires_at ? new Date(t.expires_at).toLocaleString() : '-'}</td>
                <td><code class="token-value">${t.access_token?.substring(0, 16)}...</code></td>
                <td><code class="token-value">${t.refresh_token?.substring(0, 16)}...</code></td>
                <td class="actions">
                    ${t.access_token ? `<button class="btn-danger btn-sm revoke-access" data-token="${t.access_token}" data-type="access">Отозвать access</button>` : ''}
                    ${t.refresh_token ? `<button class="btn-danger btn-sm revoke-refresh" data-token="${t.refresh_token}" data-type="refresh">Отозвать refresh</button>` : ''}
                </td>
            </tr>
        `).join('');
        attachUserTokenHandlers();
    } catch (err) {
        document.getElementById('tokensList').innerHTML = `<tr><td colspan="8">Ошибка: ${err.message}</td></tr>`;
    }
}

function attachUserTokenHandlers() {
    document.querySelectorAll('.revoke-access').forEach(btn => {
        btn.onclick = async () => {
            const token = btn.getAttribute('data-token');
            await revokeUserToken(currentUserId, token, 'access');
        };
    });
    document.querySelectorAll('.revoke-refresh').forEach(btn => {
        btn.onclick = async () => {
            const token = btn.getAttribute('data-token');
            await revokeUserToken(currentUserId, token, 'refresh');
        };
    });
}

async function revokeUserToken(userId, token, tokenType) {
    if (!confirm(`Отозвать ${tokenType} токен пользователя?`)) return;
    try {
        await apiCall(`/api/v0/admin/users/${userId}/tokens/revoke`, 'POST', { token, token_type: tokenType });
        showToast('Токен отозван', 'success');
        loadTokensForUser(userId);
        loadMyTokens();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function revokeAllUserTokens(userId, useAltEndpoint = false) {
    if (!userId) {
        showToast('Выберите пользователя', 'error');
        return;
    }
    const confirmMsg = useAltEndpoint ?
        'Отозвать ВСЕ токены пользователя' :
    showCustomConfirm(confirmMsg, async () => {
        try {
            await apiCall(`/api/v0/admin/revoke/user/${userId}`, 'POST');
            showToast('Все токены отозваны', 'success');
            loadTokensForUser(userId);
            loadMyTokens();
        } catch (err) {
            showToast(err.message, 'error');
        }
    }, document.getElementById('revokeAllUserTokensAltBtn'));
}

async function loadMyTokens() {
    try {
        const data = await apiCall('/api/v0/admin/user/active', 'GET');
        const tokens = data.active_tokens || [];
        const tbody = document.getElementById('myTokensList');
        if (!tokens.length) {
            tbody.innerHTML = '<tr><td colspan="8">Нет активных токенов</td></tr>';
            return;
        }
        tbody.innerHTML = tokens.map(t => `
            <tr>
                <td>${t.token_type || 'opaque'}</td>
                <td><code>${t.client_id}</code></td>
                <td>${t.scope || '-'}</td>
                <td>${t.issued_at ? new Date(t.issued_at).toLocaleString() : '-'}</td>
                <td>${t.expires_at ? new Date(t.expires_at).toLocaleString() : '-'}</td>
                <td><code class="token-value">${t.access_token?.substring(0, 16)}...</code></td>
                <td><code class="token-value">${t.refresh_token?.substring(0, 16)}...</code></td>
                <td class="actions">
                    ${t.access_token ? `<button class="btn-danger btn-sm revoke-my-access" data-token="${t.access_token}" data-type="access">Отозвать access</button>` : ''}
                    ${t.refresh_token ? `<button class="btn-danger btn-sm revoke-my-refresh" data-token="${t.refresh_token}" data-type="refresh">Отозвать refresh</button>` : ''}
                </td>
            </tr>
        `).join('');
        attachMyTokenHandlers();
    } catch (err) {
        document.getElementById('myTokensList').innerHTML = `<tr><td colspan="8">Ошибка: ${err.message}</td></tr>`;
    }
}

function attachMyTokenHandlers() {
    document.querySelectorAll('.revoke-my-access').forEach(btn => {
        btn.onclick = async () => {
            const token = btn.getAttribute('data-token');
            await revokeMyToken(token, 'access');
        };
    });
    document.querySelectorAll('.revoke-my-refresh').forEach(btn => {
        btn.onclick = async () => {
            const token = btn.getAttribute('data-token');
            await revokeMyToken(token, 'refresh');
        };
    });
}

async function revokeMyToken(token, tokenType) {
    if (!confirm(`Отозвать свой ${tokenType} токен?`)) return;
    try {
        await apiCall('/api/v0/admin/revoke', 'POST', { token, token_type: tokenType });
        showToast('Токен отозван', 'success');
        loadMyTokens();
        const userId = document.getElementById('tokenUserSelect').value;
        if (userId) loadTokensForUser(parseInt(userId));
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// --- Модальные окна и инициализация ---
function initModals() {
    const clientModal = document.getElementById('createClientModal');
    const openClientBtn = document.getElementById('openCreateClientModalBtn');
    const closeClient = document.querySelector('.close-client');
    if (openClientBtn) openClientBtn.onclick = () => clientModal.style.display = 'flex';
    if (closeClient) closeClient.onclick = () => clientModal.style.display = 'none';
    const confirmCreateClient = document.getElementById('confirmCreateClientBtn');
    if (confirmCreateClient) confirmCreateClient.onclick = createClientFromModal;

    const editModal = document.getElementById('editUserModal');
    const closeEdit = document.querySelector('.close-edit');
    if (closeEdit) closeEdit.onclick = () => editModal.style.display = 'none';
    const updateBtn = document.getElementById('updateUserBtn');
    if (updateBtn) updateBtn.onclick = async () => {
        const id = document.getElementById('editUserId').value;
        const email = document.getElementById('editUserEmail').value.trim();
        const full_name = document.getElementById('editUserFullName').value.trim();
        const password = document.getElementById('editUserPassword').value;
        const is_active = document.getElementById('editUserIsActive').checked;
        await updateUser(id, email, full_name, password, is_active);
    };

    const createModal = document.getElementById('createUserModal');
    const openCreateBtn = document.getElementById('openCreateUserModalBtn');
    const closeCreate = document.querySelector('.close-create');
    if (openCreateBtn) openCreateBtn.onclick = () => createModal.style.display = 'flex';
    if (closeCreate) closeCreate.onclick = () => createModal.style.display = 'none';
    const confirmCreateUser = document.getElementById('confirmCreateUserBtn');
    if (confirmCreateUser) confirmCreateUser.onclick = createUserFromModal;

    window.onclick = (e) => {
        if (e.target === clientModal) clientModal.style.display = 'none';
        if (e.target === editModal) editModal.style.display = 'none';
        if (e.target === createModal) createModal.style.display = 'none';
    };
}

function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
            if (btn.dataset.tab === 'clients') loadClients();
            if (btn.dataset.tab === 'users') loadUsers();
            if (btn.dataset.tab === 'tokens') {
                loadUsers();
                loadMyTokens();
            }
        });
    });
}

function initTokenControls() {
    const userSelect = document.getElementById('tokenUserSelect');
    if (userSelect) {
        userSelect.addEventListener('change', (e) => {
            const userId = e.target.value;
            if (userId) loadTokensForUser(parseInt(userId));
            else document.getElementById('tokensList').innerHTML = '<tr><td colspan="8">Выберите пользователя</td></tr>';
        });
    }
    const refreshBtn = document.getElementById('refreshTokensBtn');
    if (refreshBtn) refreshBtn.onclick = () => {
        const userId = document.getElementById('tokenUserSelect').value;
        if (userId) loadTokensForUser(parseInt(userId));
    };
    const revokeAllBtn = document.getElementById('revokeAllUserTokensBtn');
    if (revokeAllBtn) revokeAllBtn.onclick = () => {
        const userId = document.getElementById('tokenUserSelect').value;
        revokeAllUserTokens(userId, false);
    };
    const revokeAllAltBtn = document.getElementById('revokeAllUserTokensAltBtn');
    if (revokeAllAltBtn) revokeAllAltBtn.onclick = () => {
        const userId = document.getElementById('tokenUserSelect').value;
        revokeAllUserTokens(userId, true);
    };
    const refreshMyBtn = document.getElementById('refreshMyTokensBtn');
    if (refreshMyBtn) refreshMyBtn.onclick = () => loadMyTokens();

    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) logoutBtn.onclick = logout;
}

initTabs();
initModals();
initTokenControls();
loadClients();
loadUsers();