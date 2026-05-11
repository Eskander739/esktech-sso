#!/bin/bash

HOST_IP=$(hostname -I | awk '{print $1}')

if [ -z "$HOST_IP" ]; then
    echo "Ошибка: не удалось получить IP адрес"
    exit 1
fi

echo "Используемый IP адрес: $HOST_IP"

cat > san.cnf << EOF
[req]
default_bits = 4096
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = req_ext

[dn]
CN = app
CN = $HOST_IP

[req_ext]
subjectAltName = @alt_names

[v3_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = app
DNS.2 = localhost
DNS.3 = host.containers.internal
IP.1 = 127.0.0.1
IP.2 = $HOST_IP
EOF

echo "Конфигурационный файл san.cnf создан"

openssl req -x509 -newkey rsa:4096 \
  -keyout server.key \
  -out server.crt \
  -days 365 \
  -nodes \
  -config san.cnf

echo "Сертификат и ключ созданы:"
echo "  - server.key (приватный ключ)"
echo "  - server.crt (сертификат)"