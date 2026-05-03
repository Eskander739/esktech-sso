# EskTech SSO — лёгкий корпоративный SSO на Python

![License](https://img.shields.io/badge/license-AGPLv3-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

**EskTech SSO** — российский корпоративный сервис единого входа (Single Sign-On). Объединяет Jira, GitLab, 1С, Битрикс24, МойОфис, VK Teams и любые другие сервисы через стандартные протоколы OIDC, SAML, LDAP и OAuth2.

🔐 **Код открыт. Никаких сюрпризов.**
### ✨ **Активная стадия разработки, определенные функциональности могут не работать**
### При возникновении вопросов писать: 
#### email    - eskander5765@yandex.ru
#### telegram - @ighill2

---

## ✨ Возможности
| Возможность | Community | Enterprise Light | Enterprise Max |
|-------------|:---------:|:----------------:|:--------------:|
| Единый вход для всех сервисов | ✅ | ✅ | ✅ |
| OIDC / OAuth2 провайдер | ✅ | ✅ | ✅ |
| LDAP-адаптер (AD / OpenLDAP) | ✅ | ✅ | ✅ |
| JWT-верификация | ✅ | ✅ | ✅ |
| SAML 2.0 | ❌ | ❌ | ✅ |
| Адаптер для 1С | ❌ | ❌ | ✅ |
| Адаптер для Битрикс24 | ❌ | ❌ | ✅ |
| Количество сервисов | до 2 | до 10 | безлимит |
| Количество источников истины | 1 | до 3 | безлимит |
| Техподдержка | ❌ | 8/5 (рабочие часы) | 24/7 |
| SLA | ❌ | 99.5% | 99.9% |
| Обновления и патчи | сообщество | приоритетные | критические в течение 24ч |
| **Цена** | **0 ₽** | **240 000 ₽/год** | **590 000 ₽/год** |
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
#### Необходимо, чтобы запуск происходил из корневой директории проекта(где лежит Dockerfile, директория app и т.д)

```yaml
version: '3.8'

services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: sso_user
      POSTGRES_PASSWORD: sso_pass
      POSTGRES_DB: sso
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+asyncpg://sso_user:sso_pass@db:5432/sso
      REDIS_URL: redis://redis:6379/0

volumes:
  postgres_data:
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

### 1С (через Nginx-прокси) - ведется разработка
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
### Битрикс24 On-Premise (LDAP)  - ведется разработка
Настройте LDAP-адаптер в Битрикс24, указав EskTech как LDAP-сервер

### 🏗 Архитектура
Монолит на FastAPI с модульной структурой:

```yaml
esktech-sso
├─ app/ # Основной код приложения
│  ├── db # Работа с БД
│  │   ├── database.py # Подключение к PostgreSQL (async), движок, сессии
│  │   ├── models.py # SQLAlchemy модели (User, OAuthClient, OAuthCode, OAuthToken)
│  │   │   ├── auth_models.py # Модели авторизации
│  │   │   ├── base.py # Базовая модель
│  │   │   └── user_models.py # Модели пользователей
│  │   ├── oauth.py # Класс для взаимодействия с авторизацией
│  │   └── users.py # Класс для взаимодействия с пользователями
│  ├── endpoints # API эндпоинты
│  │   ├── oidc.py # OIDC: /authorize, /token, /userinfo, /jwks, discovery
│  │   ├── admin.py # Админка OIDC-клиентов (создание, удаление)
│  │   ├── users.py # CRUD пользователей (список, создание, редактирование, удаление)
│  │   └── health.py # Healthchecks (/health/live, /health/ready)
│  ├── schemas # Pydantic модели (UserCreate, UserUpdate)
│  │   └── users.py # Модели пользователей для запросов
│  ├── services # Бизнес-логика
│  │   └── db_pool.py # Пул соединений с базой данных
│  ├── templates_static # HTML шаблоны (Jinja2)
│  │   ├── admin_clients.html # Админка OIDC-клиентов
│  │   ├── admin_users.html # Список пользователей (админка)
│  │   ├── admin_user_form.html # Форма создания/редактирования пользователя
│  │   └── login.html # Страница логина
│  ├── tests # Тесты
│  │   ├── e2e # Сквозные тесты
│  │   ├── integration # Интеграционные тесты
│  │   ├── unit # Unit-тесты
│  │   ├── config_tests_sample.py # Конфиг тестов
│  │   └── conftest.py # Фикстуры (клиент, БД для тестов)
│  ├── utils # Утилиты
│  │   ├── cli.py # CLI для взаимодействия с командной строкой
│  │   ├── ldap_client.py # Подключение к LDAP/Active Directory
│  │   ├── license.py # Проверка лицензии (Community / Enterprise)
│  │   ├── limits.py # Проверка лимитов Community (не более 2 клиентов / 1 источника)
│  │   ├── password_validator.py # Хеширование и проверка паролей (bcrypt)
│  │   └── user_source.py # Абстракция: аутентификация через БД или LDAP
│  ├── auth_server.py # OIDC-сервер на Authlib (гранты, токены, клиенты)
│  ├── config.py # Конфигурация (Pydantic Settings, переменные окружения)
│  ├── constants.py # Константные переменные
│  ├── log.py # Система логгирования
│  └── main.py # FastAPI приложение, lifespan, роутеры
├── .env.example # Пример переменных окружения
├── .gitignore # Файл для игнорирования мусора при работа с Git
├── docker-compose.yml # PostgreSQL, Redis, приложение
├── Dockerfile # Сборка образа (Python 3.12-slim + зависимости)
├── LICENSE # AGPLv3
├── Makefile # Утилиты: run, test, format, deps
├── pyproject.toml # Poetry конфигурация (для разработки)
└── requirements.txt # Python зависимости (pip)
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
