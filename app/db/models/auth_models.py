from datetime import UTC, datetime

from constants import AccessTokenFormat, UserRole
from db.models.base import Base
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, Enum as SQLAEnum


class OAuthClientModel(Base):
    __tablename__ = "oauth_clients"

    id = Column(Integer, primary_key=True)
    client_id = Column(String(255), unique=True, nullable=False)
    client_secret = Column(String(255), nullable=False)
    client_id_issued_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    client_secret_expires_at = Column(DateTime, nullable=True)
    redirect_uris = Column(Text, nullable=False)  # JSON строка или список через запятую
    grant_types = Column(String(255), nullable=True)
    response_types = Column(String(255), nullable=True)
    scope = Column(String(255), nullable=True)
    token_endpoint_auth_method = Column(String(50), default="client_secret_basic")
    application_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)


class OAuthCodeModel(Base):
    __tablename__ = "oauth_codes"

    code = Column(String(255), primary_key=True)
    client_id = Column(String(255), nullable=False)
    redirect_uri = Column(Text, nullable=False)
    user_id = Column(Integer, nullable=False)
    scope = Column(String(255), nullable=True)
    nonce = Column(String(255), nullable=True)
    code_challenge = Column(String(255), nullable=True)
    code_challenge_method = Column(String(20), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class OAuthTokenModel(Base):
    __tablename__ = "oauth_tokens"

    id = Column(Integer, primary_key=True)
    client_id = Column(String(255), nullable=False)
    user_id = Column(Integer, nullable=True)
    role = Column(
        SQLAEnum(UserRole,
                 values_callable=lambda x: [e.value for e in x],
                 name="user_role"),
        default=UserRole.USER,
        nullable=False,
        index=True
    )
    token_type = Column(String(50), default=AccessTokenFormat.JWT)  # "jwt" или "opaque"
    access_token = Column(String(1024), unique=True, nullable=False)
    refresh_token = Column(String(1024), unique=True, nullable=True)
    scope = Column(String(255), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)
    issued_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
