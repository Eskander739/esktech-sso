[![Stars](https://img.shields.io/github/stars/Eskander739/esktech-sso?style=social)](https://github.com/Eskander739/esktech-sso)
[![Forks](https://img.shields.io/github/forks/Eskander739/esktech-sso?style=social)](https://github.com/Eskander739/esktech-sso)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
# EskTech.Единый вход — бесплатный лёгкий корпоративный SSO на Python
![Python](https://img.shields.io/badge/python-3.10%2B-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![OIDC](https://img.shields.io/badge/OIDC-1.0-blue.svg)
![SAML](https://img.shields.io/badge/SAML-2.0-orange.svg)
![LDAP](https://img.shields.io/badge/LDAP-ready-green.svg)
![Opaque Tokens](https://img.shields.io/badge/Opaque-Tokens%20%26%20Revocation-6A0DAD)
![SSO](https://img.shields.io/badge/SSO-Free-green.svg)
![SSO](https://img.shields.io/badge/SSO-Russian-blue.svg)

### **EskTech SSO** - Keycloak alternative

**EskTech.Единый вход** - российский корпоративный сервис единого входа (Single Sign-On). Объединяет Jira, GitLab, 1С, Битрикс24, МойОфис, VK Teams и любые другие сервисы через стандартные протоколы OIDC, SAML, LDAP и OAuth2.

🔐 **Код открыт. Никаких сюрпризов.**
### ✨ **Активная стадия разработки, определенные функциональности могут не работать**
### При возникновении вопросов писать: 
#### email    - eskander5765@yandex.ru
#### telegram - @ighill2

---

### ⚙️ Дорожная карта тестирования интеграции с сервисами

| Протокол | Статус |                                Сервис                                |
|-------------|:-----------------:|:--------------------------------------------------------------------:|
|OIDC	|✅	| GitLab (***протестировано***) 
|SAML 2.0	|❌	|                      Jira Atlassian(***следующий***)      
|OAuth 2.0	|❌	|                       Yandex ID                      
|SAML 2.0	|❌	|                       ЕСИА (Госуслуги)                 
|LDAP	|❌	|       Jira On-Premise, Битрикс24 On-Premise, корпоративные VPN       
|JWT (прокси)	|❌	|                     1С, любые кастомные системы

## 🚀 Старт EskTech SSO с Gitlab 

#### Предварительные работы

- Заменить ip https://192.168.1.104:8000 на ip вашей хостовой машины(скрипт: ```hostname -I```) в файлах:
1) config.py
2) .env
3) connect-gitlab-sso.sh
- Пересобрать сертификаты через generate-certs.sh(выполнить запуск в корневой директории проекта)

#### Развертывание EskTeck SSO с Gitlab
- Иметь предустановленную систему podman/docker
- Перейти в корневую директорию проекта
- Выполнить сборку docker-compose-gitlab.yml | через make podman-build или свой скрипт
- Выполнить запуск docker-compose-gitlab.yml | через make podman-up или свой скрипт
- Подождать 2-3 минуты прогрузки Gitlab
- Выполнить запуск скрипта ***connect-gitlab-sso.sh***
- Дождаться окончания выполнения скрипта + ожидание в 1-2 минуты реконфигурации Gitlab
- Добавить пользователя через https://<ваш-ip>/api/v0/admin/clients -> секция Пользователей
- Выполнить вход в Gitlab через EskTech SSO(будет кнопка снизу на странице входа)
- Вввести логин и пароль от созданного пользователя и нажать кнопку входа


## ✨ Возможности
| Возможность | EskTech SSO (Полностью бесплатно) |
|-------------|:---------------------------------:|
| Единый вход для всех сервисов | ✅ |
| OIDC / OAuth2 провайдер | ✅ |
| LDAP-адаптер (AD / OpenLDAP) | ✅ |
| JWT-верификация | ✅ |
| Opaque-токены (удалённый отзыв токенов) | ✅ |
| SAML 2.0 | ✅ (планируется) |
| Адаптер для 1С | ✅ (планируется) |
| Адаптер для Битрикс24 | ✅ (планируется) |
| Количество сервисов | безлимит |
| Количество источников истины | безлимит |
| Техподдержка | сообщество / автор проекта |
| Обновления и патчи | открытый репозиторий |
| **Цена** | **0 ₽** |

### 🔧 Поддерживаемые протоколы


| Протокол | Статус | Для каких сервисов |
|-------------|:-----------------:|:------------------:|
|OIDC	|✅	|Jira Cloud, GitLab, VK Teams, МойОфис, Grafana, Kibana, сотни других
|LDAP	|✅	|Jira On-Premise, Битрикс24 On-Premise, корпоративные VPN(планируется)
|JWT (прокси)	|✅	|1С, любые кастомные системы(планируется)
|SAML 2.0	|🚧	|Legacy-системы, госсектор(планируется)
|OAuth2	|✅	|API-шлюзы, микросервисы(планируется)

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
│  │   ├── models.py # SQLAlchemy модели (User, OAuthClient, OAuthCode, OAuthToken)
│  │   │   ├── auth_models.py # Модели авторизации
│  │   │   ├── base.py # Базовая модель
│  │   │   └── user_models.py # Модели пользователей
│  │   ├── oauth.py # Класс для взаимодействия с авторизацией
│  │   └── users.py # Класс для взаимодействия с пользователями
│  ├── endpoints # API эндпоинты
│  │   ├── oidc # Статичные эндпоинты SSO для OIDC
│  │   │   └── oidc_api.py # OIDC: /authorize, /token, /userinfo, /jwks, discovery
│  │   └── v0 # Версия API v0
│  │       ├── admin.py # Админка OIDC-клиентов (создание, удаление)
│  │       ├── users.py # CRUD пользователей (список, создание, редактирование, удаление)
│  │       └── health.py # Healthchecks (/health/live, /health/ready)
│  ├── locale # Интернационализация(eng, rus)
│  ├── models # Pydantic модели
│  │   ├── general.py # Общие модели
│  │   ├── msg.py # Общие сообщения
│  │   └── users.py # Модели пользователей для запросов
│  ├── services # Бизнес-логика
│  │   ├── pool # Директория с пулами соединений сервисов
│  │   │   ├── db_pool.py # Пул соединений БД(PostgreSQL)
│  │   │   └── redis_pool.py # # Пул соединений Redis
│  │   ├── localization.py # Класс для работы с интернационализацией
│  │   ├── redis_srv.py # Класс для работы с Redis
│  │   └── sources.py # Аутентификация пользователя по всем доступным источникам
│  ├── templates_static # HTML шаблоны (Jinja2)
│  │   ├── admin_clients.html # Админка OIDC-клиентов
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
│  │   ├── password_validator.py # Хеширование и проверка паролей (bcrypt)
│  │   └── secrets.py # Инструменты для работы с секретными ключами
│  ├── auth_server.py # OIDC-сервер на Authlib (гранты, токены, клиенты)
│  ├── config.py # Конфигурация (Pydantic Settings, переменные окружения)
│  ├── constants.py # Константные переменные
│  ├── log.py # Система логгирования
│  └── main.py # FastAPI приложение, lifespan, роутеры
├── docs # Обновления проекта
├── .env.example # Пример переменных окружения
├── .gitignore # Файл для игнорирования мусора при работа с Git
├── CODE_OF_CONDUCT.md # Кодекс поведения участника
├── connect-gitlab-sso.sh # Скрипт для подключения EskTech.Единый вход в Gitlab
├── CONTRIBUTING.md # Как внести вклад в EskTech SSO
├──docker-compose-gitlab.yml # Файл для развертывания EskTech.Единый вход с Gitlab
├── Dockerfile # Сборка образа (Python 3.12-slim + зависимости)
├── generate-certs.sh # Скрипт сборки сертификатов для EskTech.Единый вход
├── generate_rsa_keys.sh # Скрипт для генерации RSA-ключей (2048 бит) SSO-сервера
├── LICENSE # AGPLv3
├── Makefile # Утилиты: run, test, format, deps
├── pyproject.toml # Poetry конфигурация (для разработки)
├── requirements.txt # Python зависимости (pip)
└── SECURITY.md # Политика безопасности
```
#### Стек: FastAPI + PostgreSQL + Redis + Docker

### 🤝 Лицензия

**EskTech SSO** распространяется под лицензией **GNU AGPL v3**.

Код полностью открыт, вы можете использовать продукт бесплатно для любых целей.

Коммерческая поддержка и дополнительные сервисы (мониторинг безопасности, PAM, RBAC) предоставляются отдельно — по запросу.
### 📞 Контакты

Email: eskander5765@yandex.ru

### ⭐ Поддержка проекта
Если вам полезен EskTech SSO:

#### · Поставьте звезду на GitHub
#### · Расскажите коллегам
#### · Пришлите pull request

Российская разработка. Сделано с нуля.
