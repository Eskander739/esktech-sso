export function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

export default class ApiClient {
    constructor(baseURL) {
        this.baseURL = baseURL;
    }

    async request(method, endpoint, data = null, headers = {}, content = true) {
        const normalizedEndpoint = endpoint.replace(/^\/+/, '');
        const url = `${this.baseURL}/${normalizedEndpoint}`;
        let finalHeaders = {};
        if (headers["Content-Type"]) {
            finalHeaders["Content-Type"] = headers["Content-Type"];
        } else {
            finalHeaders["Content-Type"] = "application/json";
        }
        console.log('Request URL:', url);

        const config = {
            method,
            headers: finalHeaders,
            credentials: 'include',
            mode: 'cors'
        };

        if (data) {
            config.body = JSON.stringify(data);
        }

        const response = await fetch(url, config);

        // Если запрос вернул редирект, возвращаем информацию о нём
        if (response.redirected) {
            console.log('Response redirected to:', response.url);
        }

        if (content === true) {
            // Проверяем Content-Type перед парсингом JSON
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('text/html')) {
                // Если пришёл HTML, возвращаем текст и флаг, что это HTML
                const html = await response.text();
                return { __isHtml: true, html: html, status: response.status, redirected: response.redirected, url: response.url };
            }
            return await response.json();
        } else {
            return response;
        }
    }

    async requestForm(method, endpoint, formData, headers = {}, content = true) {
        const normalizedEndpoint = endpoint.replace(/^\/+/, '');
        const url = `${this.baseURL}/${normalizedEndpoint}`;

        const finalHeaders = {
            'Content-Type': 'application/x-www-form-urlencoded',
            ...headers
        };

        console.log('Form Request URL:', url);

        const config = {
            method,
            headers: finalHeaders,
            credentials: 'include',
            mode: 'cors'
        };

        if (formData) {
            config.body = new URLSearchParams(formData).toString();
        }

        const response = await fetch(url, config);

        if (content === true) {
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('text/html')) {
                const html = await response.text();
                return { __isHtml: true, html: html, status: response.status, redirected: response.redirected, url: response.url, ok: response.ok };
            }

            if (response.ok) {
                try {
                    return await response.json();
                } catch {
                    return { __isHtml: false, ok: response.ok, status: response.status };
                }
            } else {
                return { ok: false, status: response.status, statusText: response.statusText };
            }
        } else {
            return response;
        }
    }

    async get(endpoint, headers = {}) {
        return this.request('GET', endpoint, null, headers);
    }

    async getImage(endpoint, headers = {}, content = false) {
        return this.request('GET', endpoint, null, headers, content);
    }

    async post(endpoint, data, headers = {}, content = true) {
        return this.request('POST', endpoint, data, headers, content);
    }

    async postForm(endpoint, formData, headers = {}, content = true) {
        return this.requestForm('POST', endpoint, formData, headers, content);
    }

    async put(endpoint, data, headers = {}, content = true) {
        return this.request('PUT', endpoint, data, headers, content);
    }

    async delete(endpoint, headers = {}, content = true) {
        return this.request('DELETE', endpoint, null, headers, content);
    }

    // --- Специфичные методы для токенов ---
    async getUserTokens(userId) {
        return this.request('GET', `/api/v0/admin/users/${userId}/tokens`);
    }

    async revokeUserToken(userId, token, tokenType = 'access') {
        return this.request('POST', `/api/v0/admin/users/${userId}/tokens/revoke`, { token, token_type: tokenType });
    }

    async revokeAllUserTokens(userId) {
        return this.request('POST', `/api/v0/admin/users/${userId}/tokens/revoke_all`);
    }
}

export function synchronousApiCall(url) {
    var request = new XMLHttpRequest();
    request.open('GET', url, false);
    request.withCredentials = true;
    request.setRequestHeader('Content-Type', 'application/json');
    request.send();
    if (request.status >= 200 && request.status < 300) {
        return JSON.parse(request.responseText);
    } else {
        throw new Error(`Ошибка запроса: ${request.status} ${request.statusText}`);
    }
}

export async function streamToBinaryData(readableStream) {
    const reader = readableStream.getReader();
    const chunks = [];
    let totalLength = 0;
    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            chunks.push(value);
            totalLength += value.length;
        }
        const binaryData = new Uint8Array(totalLength);
        let offset = 0;
        for (const chunk of chunks) {
            binaryData.set(chunk, offset);
            offset += chunk.length;
        }
        return binaryData;
    } finally {
        reader.releaseLock();
    }
}

export async function setBackgroundImage(binaryData, mimeType = 'image/png') {
    const blob = new Blob([binaryData], { type: mimeType });
    const dataUrl = await new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.readAsDataURL(blob);
    });
    return `url('${dataUrl}')`;
}