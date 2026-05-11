"""Конфигурация приложения."""
import os
from typing import Any

from constants import AccessTokenFormat
from pydantic import Field
from pydantic_settings import BaseSettings
from utils.secrets import get_or_create_secret_key


class Settings(BaseSettings):
    """Настройки приложения."""

    # Общие
    SECRET_KEY: str = Field(default_factory=get_or_create_secret_key)
    LOCALE_DEFAULT: str = Field("en")
    ACCESS_TOKEN_FORMAT: str = Field(AccessTokenFormat.JWT)
    DEBUG: bool = Field(False)

    # База данных
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://sso_user:sso_pass@db:5432/sso",
    )
    REDIS_URL: str = Field(
        "redis://redis:6379/0",
    )

    # OIDC
    ISSUER: str = Field("https://192.168.1.104:8000")
    OIDC_CLIENT_ID: str = Field("")
    OIDC_CLIENT_SECRET: str = Field("")

    # LDAP
    LDAP_URI: str = Field("localhost")
    LDAP_BASE_DN: str = Field("")
    LDAP_BIND_DN: str = Field("")
    LDAP_BIND_PASSWORD: str = Field("")
    LDAP_USER_ATTR: str = Field("uid")


    # Лимиты
    COMMUNITY_MAX_CLIENTS: int = Field(2)
    COMMUNITY_MAX_SOURCES: int = Field(1)

    # Redis

    REDIS_POOL_SIZE: int = 10
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: str = "6379"
    REDIS_DB_PASSWORD: str = "AD34H667J6FHWQ32"
    REDIS_DB_NUMBER: int = 0
    REDIS_CACHE_REQUESTS_DB_NUMBER: int = 0
    PRIVATE_KEY_PATH: Any = os.getenv('PRIVATE_KEY_PATH', '/app/keys/private.pem')
    PUBLIC_KEY_PATH: Any = os.getenv('PUBLIC_KEY_PATH', '/app/keys/public.pem')

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


settings = Settings() # type: ignore
