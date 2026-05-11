FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    gcc \
    libldap2-dev \
    libsasl2-dev \
    curl \
    nano \
    openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml poetry.lock* ./

RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi

COPY app/ .
COPY generate_rsa_keys.sh .

RUN mkdir -p /app/keys && \
    chmod +x generate_rsa_keys.sh && \
    ./generate_rsa_keys.sh

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["poetry", "run", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000", "--ssl-keyfile", "/app/server.key", "--ssl-certfile", "/app/server.crt"]