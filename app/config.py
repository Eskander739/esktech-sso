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
    ACCESS_TOKEN_FORMAT: str = Field(AccessTokenFormat.OPAQUE)
    DEBUG: bool = Field(False)

    # База данных
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://sso_user:sso_pass@db:5432/sso",
    )
    REDIS_URL: str = Field(
        "redis://redis:6379/0",
    )

    # OIDC
    ADMIN_USERNAME: str = Field("admin")
    ADMIN_EMAIL: str = Field("admin@mail.ru")
    ADMIN_PASSWORD: str = Field("1234")
    ISSUER: str = Field("https://192.168.1.104:8000")
    OIDC_CLIENT_ID: str = Field("")
    OIDC_CLIENT_SECRET: str = Field("")

    # OpenID Configuration endpoints
    OIDC_AUTHORIZATION_ENDPOINT: str | None = Field(None,description="URL для авторизации (OAuth 2.0 Authorization Endpoint)")
    OIDC_TOKEN_ENDPOINT: str | None = Field(None, description="URL для получения токенов (Token Endpoint)")
    OIDC_USERINFO_ENDPOINT: str | None = Field(None, description="URL для получения информации о пользователе (UserInfo Endpoint)")
    OIDC_JWKS_URI: str | None = Field(None, description="URL для получения публичных ключей (JWKS URI)")

    # OpenID Configuration supported features
    OIDC_RESPONSE_TYPES_SUPPORTED: list[str] = Field(default=["code"],description="Поддерживаемые типы ответов OAuth 2.0")
    OIDC_GRANT_TYPES_SUPPORTED: list[str] = Field(default=["authorization_code", "refresh_token", "client_credentials"],description="Поддерживаемые типы Grant Flow")
    OIDC_SUBJECT_TYPES_SUPPORTED: list[str] = Field(default=["public"],description="Типы идентификаторов subject (public/pairwise)")
    OIDC_ID_TOKEN_SIGNING_ALG_VALUES_SUPPORTED: list[str] = Field(default=["RS256"],description="Алгоритмы подписи ID Token (RS256, HS256, ES256 и др.)")
    OIDC_SCOPES_SUPPORTED: list[str] = Field(default=["openid", "profile", "email"],description="Поддерживаемые OAuth 2.0 scopes")
    OIDC_TOKEN_ENDPOINT_AUTH_METHODS_SUPPORTED: list[str] = Field(default=["client_secret_basic"],description="Методы аутентификации клиента на токенном эндпоинте")
    OIDC_CLAIMS_SUPPORTED: list[str] = Field(default=["sub", "name", "given_name", "family_name", "preferred_username", "email", "email_verified"],description="Поддерживаемые claims (атрибуты пользователя)")

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
