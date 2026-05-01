# EskTech SSO — лёгкий корпоративный SSO на Python

![License](https://img.shields.io/badge/license-AGPLv3-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

**EskTech SSO** — российский корпоративный сервис единого входа (Single Sign-On). Объединяет Jira, GitLab, 1С, Битрикс24, МойОфис, VK Teams и любые другие сервисы через стандартные протоколы OIDC, SAML, LDAP и OAuth2.

🔐 **Код открыт. Никаких сюрпризов.**

---

## ✨ Возможности

| Возможность | Community Edition | Enterprise Edition |
|-------------|:-----------------:|:------------------:|
| Единый вход для всех сервисов | ✅ | ✅ |
| OIDC / OAuth2 провайдер | ✅ | ✅ |
| LDAP-адаптер (AD / OpenLDAP) | ✅ | ✅ |
| JWT-верификация | ✅ | ✅ |
| SAML 2.0 | ❌ | ✅ |
| Адаптер для 1С | ❌ | ✅ |
| Адаптер для Битрикс24 | ❌ | ✅ |
| Количество сервисов | до 2 | безлимит |
| Количество источников истины | 1 | безлимит |
| Техподдержка 24/7 | ❌ | ✅ |
| SLA 99.9% | ❌ | ✅ |
| **Цена** | **0 ₽** | **590 000 ₽/год** |

---

## 🚀 Быстрый старт (Community Edition)

### Docker (рекомендуемый способ)

```bash
docker run -d \
  --name esktech-sso \
  -p 8080:8080 \
  -e ADMIN_PASSWORD=your_secure_password \
  -e SECRET_KEY=your_secret_key_here \
  esktech/sso:latest
После запуска откройте http://localhost:8080
```

### Docker Compose (с PostgreSQL и Redis)

```yaml
version: '3.8'
services:
  esktech-sso:
    image: esktech/sso:latest
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/esktech
      - REDIS_URL=redis://redis:6379/0
      - ADMIN_PASSWORD=admin123
      - SECRET_KEY=your-secret-key
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=esktech

  redis:
    image: redis:7-alpine
```
```bash
docker-compose up -d
Из исходников
bash
git clone https://github.com/esktech/esktech-sso.git
cd esktech-sso
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```
### 🔧 Поддерживаемые протоколы


| Протокол | Статус | Для каких сервисов |
|-------------|:-----------------:|:------------------:|
|OIDC	|✅	|Jira Cloud, GitLab, VK Teams, МойОфис, Grafana, Kibana, сотни других
|LDAP	|✅	|Jira On-Premise, Битрикс24 On-Premise, корпоративные VPN
|JWT (прокси)	|✅	|1С, любые кастомные системы
|SAML 2.0	|🚧	|Legacy-системы, госсектор
|OAuth2	|✅	|API-шлюзы, микросервисы
### 📦 Интеграция с сервисами
#### Jira / GitLab / VK Teams (OIDC)
1. В админке сервиса добавьте OpenID Connect провайдера
2. Укажите Issuer URL, Client ID, Client Secret (из админки EskTech)
3. Включите SSO

### 1С (через Nginx-прокси)
```nginx
location / {
    auth_request /validate;
    proxy_pass http://1c-backend;
}

location = /validate {
    internal;
    proxy_pass https://esktech.example.com/verify;
    proxy_set_header Authorization "Bearer $http_authorization";
}
```
### Битрикс24 On-Premise (LDAP)
Настройте LDAP-адаптер в Битрикс24, указав EskTech как LDAP-сервер

### 🏗 Архитектура
Монолит на FastAPI с модульной структурой:

```text
esktech-sso/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── auth_server.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── models.py
│   │   └── crud.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── password_validator.py
│   │   ├── ldap_client.py
│   │   └── user_source.py
│   ├── endpoints/
│   │   ├── __init__.py
│   │   ├── oidc.py
│   │   ├── admin.py
│   │   └── health.py
│   ├── templates/
│   │   └── login.html
│   └── utils/
│       ├── __init__.py
│       ├── license.py
│       └── limits.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_password_validator.py
│   │   └── test_limits.py
│   ├── integration/
│   │   ├── __init__.py
│   │   └── test_db.py
│   └── e2e/
│       ├── __init__.py
│       └── test_auth_flow.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── pyproject.toml
└── Makefile
```
#### Стек: FastAPI + PostgreSQL + Redis + Docker

### 🤝 Лицензия
· **Community Edition** — GNU AGPL v3

· **Enterprise Edition** — коммерческая лицензия (включает адаптеры для 1С, Битрикс24, поддержку и SLA)

**Enterprise-клиенты получают ключ для снятия лимитов, доступ к приватному репозиторию с адаптерами, приоритетную техподдержку 24/7 и SLA 99.9%**

### 📞 Контакты

Email: eskander5765@yandex.ru

### ⭐ Поддержка проекта
Если вам полезен EskTech SSO:

#### · Поставьте звезду на GitHub
#### · Расскажите коллегам
#### · Пришлите pull request

Российская разработка. Сделано с нуля.
