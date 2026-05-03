"""Конфигурация приложения."""
from constants import AccessTokenFormat
from pydantic import Field
from pydantic_settings import BaseSettings
from utils.secrets import get_or_create_secret_key


class Settings(BaseSettings):
    """Настройки приложения."""

    # Общие
    SECRET_KEY: str = Field(default_factory=get_or_create_secret_key)
    LOCALE_DEFAULT: str = Field("en")
    ACCESS_TOKEN_FORMAT: str = Field(AccessTokenFormat.JWT, validation_alias="ACCESS_TOKEN_FORMAT")
    DEBUG: bool = Field(False, validation_alias="DEBUG")

    # База данных
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://sso_user:sso_pass@127.0.0.1:5432/sso",
        validation_alias="DB_URL"
    )
    REDIS_URL: str = Field(
        "redis://redis:6379/0",
        validation_alias="REDIS_URL"
    )

    # OIDC
    ISSUER: str = Field("http://localhost:8000", validation_alias="ISSUER")
    # ISSUER: str = Field("https://sso.esktech.ru", validation_alias="ISSUER")
    OIDC_CLIENT_ID: str = Field("", validation_alias="OIDC_CLIENT_ID")
    OIDC_CLIENT_SECRET: str = Field("", validation_alias="OIDC_CLIENT_SECRET")

    # LDAP
    LDAP_URI: str = Field("", validation_alias="LDAP_URI")
    LDAP_BASE_DN: str = Field("", validation_alias="LDAP_BASE_DN")
    LDAP_BIND_DN: str = Field("", validation_alias="LDAP_BIND_DN")
    LDAP_BIND_PASSWORD: str = Field("", validation_alias="LDAP_BIND_PASSWORD")
    LDAP_USER_ATTR: str = Field("uid", validation_alias="LDAP_USER_ATTR")

    # Лицензия
    LICENSE_KEY: str = Field("", validation_alias="LICENSE_KEY")

    # Лимиты
    COMMUNITY_MAX_CLIENTS: int = Field(2, validation_alias="COMMUNITY_MAX_CLIENTS")
    COMMUNITY_MAX_SOURCES: int = Field(1, validation_alias="COMMUNITY_MAX_SOURCES")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


settings = Settings() # type: ignore
