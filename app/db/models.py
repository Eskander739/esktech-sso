"""SQLAlchemy модели."""
import uuid
from datetime import UTC, datetime

from db.database import Base
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # может быть null если источник LDAP
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(UTC))


class OAuthClient(Base):
    __tablename__ = "oauth_clients"

    id = Column(Integer, primary_key=True)
    client_id = Column(String(255), unique=True, nullable=False)
    client_secret = Column(String(255), nullable=False)
    client_id_issued_at = Column(DateTime, default=lambda: datetime.now(UTC))
    client_secret_expires_at = Column(DateTime, nullable=True)
    redirect_uris = Column(Text, nullable=False)  # JSON строка или список через запятую
    grant_types = Column(String(255), nullable=True)
    response_types = Column(String(255), nullable=True)
    scope = Column(String(255), nullable=True)
    token_endpoint_auth_method = Column(String(50), default="client_secret_basic")
    application_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)


class OAuthCode(Base):
    __tablename__ = "oauth_codes"

    code = Column(String(255), primary_key=True)
    client_id = Column(String(255), nullable=False)
    redirect_uri = Column(Text, nullable=False)
    user_id = Column(Integer, nullable=False)
    scope = Column(String(255), nullable=True)
    nonce = Column(String(255), nullable=True)
    code_challenge = Column(String(255), nullable=True)
    code_challenge_method = Column(String(20), nullable=True)
    expires_at = Column(DateTime, nullable=False)


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    id = Column(Integer, primary_key=True)
    client_id = Column(String(255), nullable=False)
    user_id = Column(Integer, nullable=True)
    access_token = Column(String(255), unique=True, nullable=False)
    refresh_token = Column(String(255), unique=True, nullable=True)
    scope = Column(String(255), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    issued_at = Column(DateTime, default=lambda: datetime.now(UTC))
