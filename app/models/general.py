from uuid import uuid4

from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, List, Literal

from constants import TokenType, UserRole


class ClientCreate(BaseModel):
    name: str
    redirect_uris: str


class ServiceStatus(BaseModel):
    """Статус отдельного сервиса"""
    name: str
    status: bool
    url: Optional[str] = None
    error: Optional[str] = None
    response_time_ms: Optional[int] = None
    status_code: Optional[int] = None
    last_check: datetime = datetime.now()


class SSOReadyStatus(BaseModel):
    """Полный статус готовности SSO"""
    postgresql: bool = False
    redis: bool = False
    services: List[ServiceStatus] = []
    timestamp: datetime = datetime.now()
    overall_status: bool = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TokenOIDC(BaseModel):
    access_token: str
    refresh_token: str | None = None
    id_token: str | None = None
    token_type: str
    expires_in: int


class UserInfo(BaseModel):
    sub: str = Field(..., description="Subject - уникальный идентификатор пользователя")
    name: str = Field(default="", description="Полное имя пользователя")
    given_name: str = Field(default="", description="Имя")
    family_name: str = Field(default="", description="Фамилия")
    preferred_username: str = Field(default="", description="Предпочитаемое имя пользователя")
    email: str = Field(default="", description="Email адрес")
    email_verified: bool = Field(default=True, description="Подтвержден ли email")


class JWKDict(BaseModel):
    """Модель JSON Web Key (JWK) для RSA ключей."""

    kty: Literal["RSA", "EC", "oct"] = Field(default="RSA", description="Key Type - тип ключа (RSA, EC или oct)")
    kid: str = Field(..., description="Key ID - уникальный идентификатор ключа",examples=["gitlab-sso-key-1"])
    use: Literal["sig", "enc"] = Field(default="sig", description="Intended use of the key (sig - подпись, enc - шифрование)")
    alg: str = Field(..., description="Algorithm - алгоритм, используемый с ключом",examples=["RS256", "HS256", "ES256"])
    n: str = Field(..., description="Modulus - модуль RSA ключа (base64url encoded)",examples=["yXQ6yV9uZ2L8p3Kx..."])
    e: str = Field(..., description="Exponent - экспонента RSA ключа (base64url encoded)",examples=["AQAB"])


class JWTAccessTokenPayload(BaseModel):
    """Модель payload для JWT access token."""

    jti: str = Field(default_factory=lambda: str(uuid4()), description="JWT ID - уникальный идентификатор токена")
    sub: str = Field(..., description="Subject - идентификатор пользователя")
    client_id: str = Field(..., description="ID клиента, запросившего токен")
    scope: str = Field(default="", description="Права доступа токена")
    exp: datetime = Field( ..., description="Expiration time - время истечения токена")
    iat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Issued at - время выдачи токена")
    type: Optional[str] = Field(default="access", description="Тип токена (access/refresh)")
    role: UserRole = Field(default=UserRole.USER, description="Роль пользователя")


class RevokeAllRequest(BaseModel):
    user_id: int
    reason: str = "manual_revoke"


class RevokeTokenRequest(BaseModel):
    token: str
    token_type: TokenType = TokenType.ACCESS_TOKEN
