#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для логирования
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}[STEP]${NC} $1"
    echo -e "${GREEN}========================================${NC}\n"
}

# Определяем директорию скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_PATH="${SCRIPT_DIR}/server.crt"
KEY_PATH="${SCRIPT_DIR}/server.key"

log_info "Директория скрипта: $SCRIPT_DIR"

# Проверка на podman
if ! command -v podman &> /dev/null; then
    log_error "Podman не установлен. Установите podman и попробуйте снова."
    exit 1
fi

# Проверка на curl
if ! command -v curl &> /dev/null; then
    log_error "Curl не установлен. Установите curl и попробуйте снова."
    exit 1
fi

# Проверка наличия сертификатов
log_step "Проверка наличия сертификатов"
if [ ! -f "$CERT_PATH" ]; then
    log_error "Сертификат не найден: $CERT_PATH"
    log_info "Убедитесь, что файл server.crt находится в той же директории, что и скрипт"
    exit 1
fi

if [ ! -f "$KEY_PATH" ]; then
    log_error "Ключ не найден: $KEY_PATH"
    log_info "Убедитесь, что файл server.key находится в той же директории, что и скрипт"
    exit 1
fi
log_success "Сертификаты найдены"
log_info "  Сертификат: $CERT_PATH"
log_info "  Ключ: $KEY_PATH"

# Параметры из вашей конфигурации
CONTAINER_NAME="esktech-sso_gitlab_1"
HOST_IP="192.168.1.104"
SSO_PORT="8000"
GITLAB_PORT="8929"

log_info "Используемые параметры:"
log_info "  Имя контейнера: $CONTAINER_NAME"
log_info "  Host IP: $HOST_IP"
log_info "  SSO Port: $SSO_PORT"
log_info "  GitLab Port: $GITLAB_PORT"
log_info "  Путь к сертификату: $CERT_PATH"
log_info "  Путь к ключу: $KEY_PATH"
echo ""

# Проверка существования контейнера
log_step "Проверка существования контейнера $CONTAINER_NAME"
if ! podman ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    log_error "Контейнер $CONTAINER_NAME не найден или не запущен"
    log_info "Доступные контейнеры:"
    podman ps --format "table {{.Names}}\t{{.Status}}"
    exit 1
fi
log_success "Контейнер найден"

# Шаг 1: Создание OIDC клиента через API
log_step "Создание OIDC клиента через API SSO"

SSO_API_URL="https://${HOST_IP}:${SSO_PORT}/api/v0/admin/clients"
log_info "Отправка запроса на: $SSO_API_URL"

# Делаем curl запрос с игнорированием проверки сертификата для самоподписанных
RESPONSE=$(curl -s -k -X POST "$SSO_API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GitLab OIDC Client",
    "redirect_uris": "https://'${HOST_IP}':'${GITLAB_PORT}'/users/auth/openid_connect/callback"
  }')

# Проверяем что ответ не пустой
if [ -z "$RESPONSE" ]; then
    log_error "Пустой ответ от API SSO. Проверьте что SSO сервер запущен и доступен."
    exit 1
fi

# Извлекаем client_id и client_secret из ответа
if command -v jq &> /dev/null; then
    CLIENT_ID=$(echo "$RESPONSE" | jq -r '.client_id')
    CLIENT_SECRET=$(echo "$RESPONSE" | jq -r '.client_secret')
else
    CLIENT_ID=$(echo "$RESPONSE" | grep -o '"client_id":"[^"]*"' | cut -d'"' -f4)
    CLIENT_SECRET=$(echo "$RESPONSE" | grep -o '"client_secret":"[^"]*"' | cut -d'"' -f4)
fi

if [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ]; then
    log_error "Не удалось получить client_id и client_secret из ответа API"
    log_info "Ответ API: $RESPONSE"
    exit 1
fi

log_success "OIDC клиент успешно создан!"
log_info "  Client ID: $CLIENT_ID"
log_info "  Client Secret: $CLIENT_SECRET"

# Шаг 2: Создание директории для сертификатов в контейнере
log_step "Создание директории для сертификатов в контейнере"
if podman exec $CONTAINER_NAME mkdir -p /etc/gitlab/ssl 2>&1; then
    log_success "Директория /etc/gitlab/ssl создана"
else
    log_error "Не удалось создать директорию /etc/gitlab/ssl"
    exit 1
fi

if podman exec $CONTAINER_NAME mkdir -p /opt/gitlab/embedded/ssl/certs 2>&1; then
    log_success "Директория /opt/gitlab/embedded/ssl/certs создана"
else
    log_error "Не удалось создать директорию /opt/gitlab/embedded/ssl/certs"
    exit 1
fi

# Шаг 3: Копирование сертификатов в контейнер
log_step "Копирование сертификатов в контейнер"
CONTAINER_ID=$(podman ps --filter "name=$CONTAINER_NAME" --format "{{.ID}}")
log_info "Container ID: $CONTAINER_ID"

# Копируем сертификат для GitLab (в /etc/gitlab/ssl)
if podman cp "$CERT_PATH" ${CONTAINER_ID}:/etc/gitlab/ssl/gitlab.crt 2>&1; then
    log_success "Сертификат скопирован в /etc/gitlab/ssl/gitlab.crt"
else
    log_warning "Не удалось скопировать сертификат в /etc/gitlab/ssl"
    exit 1
fi

# Копируем ключ для GitLab (в /etc/gitlab/ssl)
if podman cp "$KEY_PATH" ${CONTAINER_ID}:/etc/gitlab/ssl/gitlab.key 2>&1; then
    log_success "Ключ скопирован в /etc/gitlab/ssl/gitlab.key"
else
    log_warning "Не удалось скопировать ключ в /etc/gitlab/ssl"
    exit 1
fi

# Устанавливаем правильные права на сертификаты
log_step "Установка прав на сертификаты"
podman exec $CONTAINER_NAME chmod 644 /etc/gitlab/ssl/gitlab.crt 2>&1
podman exec $CONTAINER_NAME chmod 600 /etc/gitlab/ssl/gitlab.key 2>&1
log_success "Права на сертификаты установлены"

# Копируем сертификат для системного доверия Ruby
log_step "Копирование сертификата для системного доверия Ruby"
if podman cp "$CERT_PATH" ${CONTAINER_ID}:/opt/gitlab/embedded/ssl/certs/esktech.crt 2>&1; then
    log_success "Сертификат скопирован в /opt/gitlab/embedded/ssl/certs/esktech.crt"

    # Создание хэш-ссылки
    log_step "Создание хэш-ссылки для сертификата"
    podman exec $CONTAINER_NAME bash -c '
        cd /opt/gitlab/embedded/ssl/certs
        HASH=$(openssl x509 -hash -noout -in esktech.crt 2>/dev/null)
        if [ -n "$HASH" ]; then
            ln -sf esktech.crt ${HASH}.0
            echo "Хэш: $HASH, ссылка создана"
        fi
    ' 2>&1
else
    log_warning "Не удалось скопировать сертификат для Ruby"
fi

# Шаг 4: Настройка gitlab.rb с полученными client_id, client_secret и сертификатами
log_step "Настройка конфигурации GitLab (gitlab.rb)"
log_info "Генерация конфигурации с полученными параметрами и сертификатами..."

# Создаем временный файл с конфигурацией
TMP_CONFIG=$(mktemp)
cat > $TMP_CONFIG << EOF
external_url "https://${HOST_IP}:${GITLAB_PORT}"
nginx["listen_port"] = ${GITLAB_PORT}
nginx["ssl_certificate"] = "/etc/gitlab/ssl/gitlab.crt"
nginx["ssl_certificate_key"] = "/etc/gitlab/ssl/gitlab.key"
nginx["ssl_verify_client"] = "off"

# Отключаем проверку SSL для внутренних запросов (для самоподписанных сертификатов)
gitlab_rails["gitlab_email_enabled"] = false
gitlab_rails["monitoring_whitelist"] = ["0.0.0.0/0"]
gitlab_rails["password_validation"] = false

# Настройки OmniAuth
gitlab_rails["omniauth_enabled"] = true
gitlab_rails["omniauth_allow_single_sign_on"] = ["openid_connect"]
gitlab_rails["omniauth_block_auto_created_users"] = false
gitlab_rails["omniauth_auto_link_ldap_user"] = false
gitlab_rails["omniauth_auto_link_saml_user"] = false
gitlab_rails["omniauth_auto_link_user"] = ["openid_connect"]

gitlab_rails["omniauth_providers"] = [
  {
    name: "openid_connect",
    label: "EskTech SSO",
    args: {
      name: "openid_connect",
      strategy_class: "OmniAuth::Strategies::OpenIDConnect",
      scope: ["openid", "profile", "email"],
      response_type: "code",
      issuer: "https://${HOST_IP}:${SSO_PORT}",
      discovery: true,
      uid_field: "preferred_username",
      client_auth_method: "basic",
      pkce: false,
      send_scope_to_token_endpoint: false,
      client_options: {
        identifier: "${CLIENT_ID}",
        secret: "${CLIENT_SECRET}",
        redirect_uri: "https://${HOST_IP}:${GITLAB_PORT}/users/auth/openid_connect/callback",
        ssl_ca_file: "/opt/gitlab/embedded/ssl/certs/esktech.crt"
      }
    }
  }
]

# Настройки для работы с самоподписанными сертификатами
gitlab_rails["curl_verify_ssl"] = false
EOF

# Показываем сгенерированную конфигурацию
log_info "Сгенерированная конфигурация:"
echo -e "${YELLOW}----------------------------------------${NC}"
cat $TMP_CONFIG
echo -e "${YELLOW}----------------------------------------${NC}"

# Копируем конфигурацию в контейнер
if podman cp $TMP_CONFIG ${CONTAINER_ID}:/etc/gitlab/gitlab.rb 2>&1; then
    log_success "Конфигурация скопирована в контейнер"
    rm -f $TMP_CONFIG
else
    log_error "Не удалось скопировать конфигурацию"
    rm -f $TMP_CONFIG
    exit 1
fi

# Шаг 5: Применение конфигурации
log_step "Применение конфигурации GitLab (gitlab-ctl reconfigure)"
log_warning "Этот процесс может занять 5-10 минут... пожалуйста, подождите"

if podman exec $CONTAINER_NAME gitlab-ctl reconfigure 2>&1; then
    log_success "Конфигурация успешно применена"
else
    log_error "Ошибка при применении конфигурации"
    exit 1
fi

# Финальная проверка
log_step "Проверка статуса GitLab"
podman exec $CONTAINER_NAME gitlab-ctl status

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ НАСТРОЙКА ЗАВЕРШЕНА!${NC}"
echo -e "${GREEN}========================================${NC}\n"

log_success "GitLab настроен со следующими параметрами:"
log_info "  URL GitLab: https://$HOST_IP:$GITLAB_PORT"
log_info "  URL SSO: https://$HOST_IP:$SSO_PORT"
log_info "  Client ID: $CLIENT_ID"
log_info "  Client Secret: $CLIENT_SECRET"
log_info "  Redirect URI: https://$HOST_IP:$GITLAB_PORT/users/auth/openid_connect/callback"
log_info "  SSL Certificate: /etc/gitlab/ssl/gitlab.crt"
log_info "  SSL Key: /etc/gitlab/ssl/gitlab.key"

echo -e "\n${YELLOW}Важно:${NC}"
echo "1. Убедитесь, что ваш SSO сервер запущен и доступен по адресу https://$HOST_IP:$SSO_PORT"
echo "2. Войдите в GitLab: https://$HOST_IP:$GITLAB_PORT"
echo "3. На странице входа появится кнопка 'EskTech SSO'"
echo "4. GitLab использует те же сертификаты, что и SSO (скопированы из директории скрипта)"

echo -e "\n${YELLOW}Полезные команды:${NC}"
echo "  Просмотр логов: podman logs -f $CONTAINER_NAME"
echo "  Остановка: podman stop $CONTAINER_NAME"
echo "  Запуск: podman start $CONTAINER_NAME"
echo "  Проверка сертификата: podman exec $CONTAINER_NAME openssl x509 -in /etc/gitlab/ssl/gitlab.crt -text -noout"

# Проверка доступности GitLab
log_step "Проверка доступности GitLab"
sleep 10

# Используем -k для игнорирования проверки сертификата при проверке
HTTP_CODE=$(curl -s -k -o /dev/null -w "%{http_code}" "https://$HOST_IP:$GITLAB_PORT" 2>/dev/null)
if [[ "$HTTP_CODE" == "200" ]] || [[ "$HTTP_CODE" == "302" ]]; then
    log_success "GitLab доступен по адресу https://$HOST_IP:$GITLAB_PORT (HTTP $HTTP_CODE)"
else
    log_warning "GitLab пока не оcdтвечает (HTTP $HTTP_CODE), возможно еще запускается. Подождите несколько минут."
    log_info "Проверить статус можно командой: podman exec $CONTAINER_NAME gitlab-ctl status"
fi

echo -e "\n${GREEN}Готово!${NC}\n"