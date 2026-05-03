import os
import secrets
from pathlib import Path

SECRETS_DIR = Path("/etc/esktech/sso")
SECRETS_FILE = SECRETS_DIR / "secret_key"


def get_or_create_secret_key() -> str:
    """Возвращает секретный ключ из файла или генерирует новый."""
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)

    if SECRETS_FILE.exists():
        return SECRETS_FILE.read_text().strip()

    # Генерируем 32-байтный ключ (256 бит)
    secret_key = secrets.token_urlsafe(32)
    SECRETS_FILE.write_text(secret_key)
    os.chmod(SECRETS_FILE, 0o600)  # только владелец

    return secret_key
