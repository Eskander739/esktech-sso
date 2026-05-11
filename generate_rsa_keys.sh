#!/bin/bash

# Скрипт для генерации RSA ключей для SSO сервера
# Использование: ./generate_rsa_keys.sh

set -e  # Останавливаем скрипт при любой ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Генерация RSA ключей для SSO сервера${NC}"
echo -e "${GREEN}========================================${NC}"

# Директория для ключей
KEYS_DIR="/app/keys"

# Проверяем, не существуют ли уже ключи
if [ -f "$KEYS_DIR/private.pem" ] || [ -f "$KEYS_DIR/public.pem" ]; then
    echo -e "${YELLOW}Внимание: Ключи уже существуют в $KEYS_DIR${NC}"
    read -p "Перезаписать? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Отмена генерации${NC}"
        exit 0
    fi
fi

# Создаем директорию
echo -e "${GREEN}1. Создаем директорию $KEYS_DIR...${NC}"
mkdir -p "$KEYS_DIR"

# Генерируем приватный ключ (2048 бит)
echo -e "${GREEN}2. Генерируем приватный ключ (2048 bit RSA)...${NC}"
openssl genrsa -out "$KEYS_DIR/private.pem" 2048

if [ $? -eq 0 ]; then
    echo -e "${GREEN}   ✓ Приватный ключ создан: $KEYS_DIR/private.pem${NC}"
else
    echo -e "${RED}   ✗ Ошибка создания приватного ключа${NC}"
    exit 1
fi

# Извлекаем публичный ключ
echo -e "${GREEN}3. Извлекаем публичный ключ...${NC}"
openssl rsa -in "$KEYS_DIR/private.pem" -pubout -out "$KEYS_DIR/public.pem"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}   ✓ Публичный ключ создан: $KEYS_DIR/public.pem${NC}"
else
    echo -e "${RED}   ✗ Ошибка создания публичного ключа${NC}"
    exit 1
fi

# Устанавливаем правильные права доступа
echo -e "${GREEN}4. Устанавливаем права доступа...${NC}"
chmod 600 "$KEYS_DIR/private.pem"
chmod 644 "$KEYS_DIR/public.pem"

echo -e "${GREEN}   ✓ Права установлены:${NC}"
echo -e "     - private.pem: 600 (только владелец)"
echo -e "     - public.pem:  644 (чтение для всех)"

# Проверяем ключи
echo -e "${GREEN}5. Проверяем ключи...${NC}"
if openssl rsa -in "$KEYS_DIR/private.pem" -check -noout 2>/dev/null; then
    echo -e "${GREEN}   ✓ Приватный ключ валидный${NC}"
else
    echo -e "${RED}   ✗ Приватный ключ невалидный${NC}"
    exit 1
fi

# Выводим информацию о ключах
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Генерация ключей завершена успешно!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Приватный ключ: ${YELLOW}$KEYS_DIR/private.pem${NC}"
echo -e "Публичный ключ: ${YELLOW}$KEYS_DIR/public.pem${NC}"
