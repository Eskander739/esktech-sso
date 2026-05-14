import ApiClient from './api.js';

// Инициализируем API клиент (пустой baseURL = текущий домен)
const api = new ApiClient('');

const form = document.getElementById('loginForm');
const messageContainer = document.getElementById('messageContainer');
const submitButton = form.querySelector('button[type="submit"]');

// Функция для отображения сообщений (ошибка/успех)
function showMessage(message, type = 'error') {
    messageContainer.innerHTML = `<div class="${type}">${message}</div>`;
    // Автоскрытие через 5 секунд для успешных сообщений
    if (type === 'success') {
        setTimeout(() => {
            if (messageContainer.firstChild) messageContainer.innerHTML = '';
        }, 5000);
    }
}

// Функция для очистки сообщений
function clearMessage() {
    messageContainer.innerHTML = '';
}

// Функция установки состояния загрузки кнопки
function setButtonLoading(isLoading) {
    if (isLoading) {
        submitButton.classList.add('loading');
        submitButton.disabled = true;
    } else {
        submitButton.classList.remove('loading');
        submitButton.disabled = false;
    }
}

// Функция для извлечения сообщения об ошибке из HTML
function extractErrorMessageFromHtml(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');

    // Ищем возможные элементы с сообщениями об ошибках
    const errorSelectors = [
        '.error-message',
        '.alert-error',
        '.alert-danger',
        '.error',
        '.message.error',
        '[role="alert"]',
        '.notification.error'
    ];

    for (const selector of errorSelectors) {
        const element = doc.querySelector(selector);
        if (element && element.textContent) {
            return element.textContent.trim();
        }
    }

    // Пытаемся найти форму с ошибкой
    const formElement = doc.querySelector('form');
    if (formElement && formElement.textContent.includes('ошибк')) {
        const errorText = formElement.textContent.match(/[^.!?]*(?:ошибк|неверн|неправильн)[^.!?]*[.!?]/i);
        if (errorText) {
            return errorText[0].trim();
        }
    }

    return null;
}

// Обработка отправки формы
form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearMessage();

    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    if (!username || !password) {
        showMessage('Заполните оба поля', 'error');
        return;
    }

    // Блокируем кнопку на время запроса
    setButtonLoading(true);

    try {
        // Используем postForm для отправки данных формы
        const response = await api.postForm('/login', { username, password });

        // Проверяем, пришёл ли HTML ответ
        if (response && response.__isHtml) {
            // Пришла HTML страница (обычно это ошибка или редирект)
            console.log('Received HTML response, status:', response.status);

            // Если произошёл редирект (успешный вход)
            if (response.redirected && response.url && !response.url.includes('/login')) {
                // Успешный вход - браузер сам обработает редирект
                showMessage('Вход выполнен успешно! Перенаправление...', 'success');
                setTimeout(() => {
                    window.location.href = response.url;
                }, 500);
                return;
            }

            // Пытаемся извлечь сообщение об ошибке из HTML
            const errorMsg = extractErrorMessageFromHtml(response.html);
            if (errorMsg) {
                showMessage(errorMsg, 'error');
            } else {
                showMessage('Неверные учётные данные', 'error');
            }
            setButtonLoading(false);
            return;
        }

        // Обработка JSON ответа
        if (response && response.ok === false) {
            showMessage(response.statusText || 'Ошибка аутентификации', 'error');
            setButtonLoading(false);
            return;
        }

        // Успешный JSON ответ
        if (response && (response.access_token || response.message === 'success' || response.status === 'success')) {
            showMessage('Вход выполнен успешно! Перенаправление...', 'success');
            setTimeout(() => {
                window.location.href = '/admin_clients.html';
            }, 1500);
        } else if (response && (response.error || response.detail)) {
            showMessage(response.error || response.detail || 'Неверные учётные данные', 'error');
            setButtonLoading(false);
        } else {
            showMessage('Неизвестная ошибка', 'error');
            setButtonLoading(false);
        }

    } catch (error) {
        console.error('Login error:', error);

        // Проверяем, не пришёл ли HTML в ошибке
        if (error.response && error.response.__isHtml) {
            const errorMsg = extractErrorMessageFromHtml(error.response.html);
            showMessage(errorMsg || 'Неверные учётные данные', 'error');
        } else if (error.message) {
            if (error.message.includes('401') || error.message.includes('400')) {
                showMessage('Неверный логин или пароль', 'error');
            } else if (error.message.includes('fetch') || error.message.includes('network')) {
                showMessage('Ошибка соединения с сервером', 'error');
            } else {
                showMessage(error.message, 'error');
            }
        } else {
            showMessage('Ошибка соединения или сервера', 'error');
        }
        setButtonLoading(false);
    }
});