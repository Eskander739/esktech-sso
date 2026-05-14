import os
from pathlib import Path

from config import settings
from log import logger


def load_rsa_keys():
    """Загружает RSA ключи из нескольких возможных мест."""
    possible_key_paths = []

    # 1. Из настроек
    if hasattr(settings, 'PRIVATE_KEY_PATH') and settings.PRIVATE_KEY_PATH:
        possible_key_paths.append(Path(settings.PRIVATE_KEY_PATH))
    if hasattr(settings, 'PUBLIC_KEY_PATH') and settings.PUBLIC_KEY_PATH:
        possible_key_paths.append(Path(settings.PUBLIC_KEY_PATH))

    # 2. Стандартные пути
    possible_key_paths.extend([
        Path("/app/keys/private.pem"),
        Path("/app/keys/public.pem"),
        Path("/app/private.pem"),
        Path("/app/public.pem"),
        Path("/etc/sso/keys/private.pem"),
        Path("/etc/sso/keys/public.pem"),
    ])

    env_private = os.getenv("SSO_PRIVATE_KEY_PATH")
    env_public = os.getenv("SSO_PUBLIC_KEY_PATH")
    if env_private:
        possible_key_paths.append(Path(env_private))
    if env_public:
        possible_key_paths.append(Path(env_public))

    private_key_path = None
    public_key_path = None

    # Ищем приватный ключ
    for path in possible_key_paths:
        if 'private' in str(path).lower() and path.exists():
            private_key_path = path
            break

    # Ищем публичный ключ
    for path in possible_key_paths:
        if 'public' in str(path).lower() and path.exists():
            public_key_path = path
            break

    private_key = None
    public_key = None

    if private_key_path and private_key_path.exists():
        try:
            with open(private_key_path, "r") as f:
                private_key = f.read()
            logger.info(f"Private key loaded from {private_key_path}")
        except Exception as e:
            logger.error(f"Failed to read private key from {private_key_path}: {e}")
    else:
        logger.error(f"Private key not found. Searched in: {[str(p) for p in possible_key_paths if 'private' in str(p).lower()]}")

    if public_key_path and public_key_path.exists():
        try:
            with open(public_key_path, "r") as f:
                public_key = f.read()
            logger.info(f"Public key loaded from {public_key_path}")
        except Exception as e:
            logger.error(f"Failed to read public key from {public_key_path}: {e}")
    else:
        logger.error(f"Public key not found. Searched in: {[str(p) for p in possible_key_paths if 'public' in str(p).lower()]}")

    return private_key, public_key
