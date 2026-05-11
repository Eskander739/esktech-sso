"""Настройка OIDC-сервера на основе Authlib с поддержкой RS256."""
import base64
import logging
import secrets
import uuid
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
from config import settings
from constants import AccessTokenFormat, GrantType
from fastapi import HTTPException, Request, status
from models.msg import Message
from services.localization import _
from starlette.responses import RedirectResponse

logger = logging.getLogger(__name__)

# Загрузка RSA ключей для RS256 - УЛУЧШЕННАЯ ВЕРСИЯ
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

    # 3. Из переменных окружения
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

# Загружаем ключи
PRIVATE_KEY, PUBLIC_KEY = load_rsa_keys()

if PRIVATE_KEY and PUBLIC_KEY:
    logger.info("✅ RSA keys loaded successfully for RS256 signing")
else:
    logger.error("❌ RSA KEYS NOT FOUND! GitLab authentication WILL FAIL!")
    logger.error("Please generate RSA keys using:")
    logger.error("  mkdir -p /app/keys")
    logger.error("  openssl genrsa -out /app/keys/private.pem 2048")
    logger.error("  openssl rsa -in /app/keys/private.pem -pubout -out /app/keys/public.pem")


class OIDCServer:
    """Простой OIDC сервер, поддерживающий JWT (RS256/HS256) и OPAQUE токены."""

    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        # GitLab требует RS256, поэтому форсируем его если ключи есть
        self.algorithm = "RS256" if PRIVATE_KEY and PUBLIC_KEY else "HS256"
        self.private_key = PRIVATE_KEY
        self.public_key = PUBLIC_KEY

        if self.algorithm == "RS256":
            logger.info(f"✅ OIDC Server initialized with RS256 (GitLab compatible)")
        else:
            logger.error(f"❌ OIDC Server initialized with {self.algorithm} - GitLab WILL FAIL!")

    async def authorize(self, request: Request, client_id: str, redirect_uri: str,
                       response_type: str, scope: str, state: str | None = None,
                       nonce: str | None = None):
        oauth_client_db = request.app.state.oauth_client_db
        oauth_code_db = request.app.state.oauth_code_db
        logger.error(f"🔥🔥🔥 AUTHORIZE CALLED with nonce={nonce}, type={type(nonce)}")
        client = await oauth_client_db.get_client(client_id)
        if not client or not client.get("is_active"):
            logger.warning(f"Invalid client or inactive: client_id={client_id}")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.invalid_client))

        allowed_uris = client.get("redirect_uris", "").split()
        if redirect_uri not in allowed_uris:
            logger.warning(f"Redirect URI mismatch: {redirect_uri} not in {allowed_uris}")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.invalid_redirect_uri))

        if response_type != "code":
            logger.warning(f"Unsupported response_type: {response_type}")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.only_authorization_code_flow_is_supported))

        user = request.session.get("user")
        if not user:
            logger.info(f"User not authenticated, saving oauth_params for client {client_id}")
            request.session["oauth_params"] = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "state": state,
                "nonce": nonce,
            }
            return RedirectResponse(url="/login")

        code = secrets.token_urlsafe(32)
        await oauth_code_db.save_code(
            code=code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            user_id=user["id"],
            scope=scope,
            nonce=nonce,
            code_challenge=None,
            code_challenge_method=None,
        )
        logger.info(f"Authorization code generated for user {user['id']}, client {client_id}, nonce={nonce}")

        redirect_url = f"{redirect_uri}?code={code}"
        if state:
            redirect_url += f"&state={state}"
        return RedirectResponse(url=redirect_url)

    async def token(self, request: Request):
        form = await request.form()
        grant_type = form.get("grant_type")

        client_id = None
        client_secret = None

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
                if ':' in decoded:
                    client_id, client_secret = decoded.split(':', 1)
                logger.info(f"Basic Auth decoded: client_id={client_id}")
            except Exception as e:
                logger.error(f"Failed to decode Basic Auth: {e}")
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid Basic Auth")

        if not client_id or not client_secret:
            logger.error("Missing client credentials in token request")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing client credentials")

        oauth_client_db = request.app.state.oauth_client_db
        oauth_code_db = request.app.state.oauth_code_db
        oauth_token_db = request.app.state.oauth_token_db
        user_db = request.app.state.user_db

        client = await oauth_client_db.get_client(client_id)
        if not client or not client.get("is_active"):
            logger.warning(f"Client not found or inactive: client_id={client_id}")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, _(Message.invalid_client))

        if client.get("client_secret") != client_secret:
            logger.warning(f"Invalid client secret for client_id={client_id}")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, _(Message.invalid_client_secret))

        token_format = settings.ACCESS_TOKEN_FORMAT

        if grant_type == GrantType.AUTHORIZATION_CODE:
            code = form.get("code")
            redirect_uri = form.get("redirect_uri")

            if not isinstance(code, str) or not isinstance(redirect_uri, str):
                logger.error("Invalid code or redirect_uri in token request")
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.invalid_or_missing_code_or_redirect_uri))

            code_data = await oauth_code_db.get_code(code)
            if not code_data:
                logger.warning(f"Invalid or expired code: {code}")
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.invalid_or_expired_code))

            if code_data["client_id"] != client_id:
                logger.warning(f"Client mismatch: expected {code_data['client_id']}, got {client_id}")
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.code_client_mismath))

            if code_data["redirect_uri"] != redirect_uri:
                logger.warning(f"Redirect URI mismatch: expected {code_data['redirect_uri']}, got {redirect_uri}")
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.redirect_uri_mismath))

            user = await user_db.get_by_id(code_data["user_id"])
            if not user:
                logger.error(f"User not found for user_id={code_data['user_id']}")
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.user_not_found))

            await oauth_code_db.delete_code(code)
            logger.info(f"Code consumed for user {user['id']}, client {client_id}")

            # Генерация токенов
            if token_format == AccessTokenFormat.OPAQUE:
                access_token = await self._create_opaque_token(
                    user_id=user["id"],
                    client_id=client_id,
                    scope=code_data["scope"],
                    oauth_token_db=oauth_token_db,
                )
                refresh_token = secrets.token_urlsafe(32)
                await oauth_token_db.save_token(
                    token={"access_token": access_token, "expires_in": 3600},
                    client_id=client_id,
                    user_id=user["id"],
                    scope=code_data["scope"],
                    refresh_token=refresh_token,
                    token_type=AccessTokenFormat.OPAQUE,
                )
            else:
                access_token = self._create_jwt_access_token(user, client_id, code_data["scope"])
                refresh_token = secrets.token_urlsafe(32)
                await oauth_token_db.save_token(
                    token={"access_token": access_token, "expires_in": 3600},
                    client_id=client_id,
                    user_id=user["id"],
                    scope=code_data["scope"],
                    refresh_token=refresh_token,
                    token_type=AccessTokenFormat.JWT,
                )

            # ВАЖНО: id_token должен включать nonce, если он был в запросе
            id_token = self._create_id_token(user, client_id, nonce=code_data.get("nonce"))
            logger.info(f"Tokens issued for user {user['id']}, client {client_id} (id_token alg={self.algorithm}, nonce={code_data.get('nonce')})")

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "id_token": id_token,
                "token_type": "Bearer",
                "expires_in": 3600,
            }

        # Остальные grant_type (refresh_token, client_credentials) без изменений
        elif grant_type == GrantType.REFRESH_TOKEN:
            refresh_token = form.get(GrantType.REFRESH_TOKEN)
            if not isinstance(refresh_token, str):
                logger.error("Missing or invalid refresh_token")
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.refresh_token_invalid_or_missing))

            token_data = await oauth_token_db.get_token_by_refresh(refresh_token)
            if not token_data or token_data.get("is_revoked"):
                logger.warning(f"Invalid or revoked refresh token: {refresh_token}")
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.refresh_token_invalid))

            if token_data["client_id"] != client_id:
                logger.warning(f"Client mismatch for refresh token: expected {token_data['client_id']}, got {client_id}")
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.client_mismath))

            user = await user_db.get_by_id(token_data["user_id"])
            if not user:
                logger.error(f"User not found for user_id={token_data['user_id']}")
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.user_not_found))

            await oauth_token_db.revoke_token(refresh_token)

            if token_format == AccessTokenFormat.OPAQUE:
                new_access_token = await self._create_opaque_token(
                    user_id=user["id"],
                    client_id=client_id,
                    scope=token_data["scope"],
                    oauth_token_db=oauth_token_db,
                )
                new_refresh_token = secrets.token_urlsafe(32)
                await oauth_token_db.save_token(
                    token={"access_token": new_access_token, "expires_in": 3600},
                    client_id=client_id,
                    user_id=user["id"],
                    scope=token_data["scope"],
                    refresh_token=new_refresh_token,
                    token_type=AccessTokenFormat.OPAQUE,
                )
            else:
                new_access_token = self._create_jwt_access_token(user, client_id, token_data["scope"])
                new_refresh_token = secrets.token_urlsafe(32)
                await oauth_token_db.save_token(
                    token={"access_token": new_access_token, "expires_in": 3600},
                    client_id=client_id,
                    user_id=user["id"],
                    scope=token_data["scope"],
                    refresh_token=new_refresh_token,
                    token_type=AccessTokenFormat.JWT,
                )

            logger.info(f"Tokens refreshed for user {user['id']}, client {client_id}")
            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "Bearer",
                "expires_in": 3600,
            }

        elif grant_type == GrantType.CLIENT_CREDENTIALS:
            if token_format == AccessTokenFormat.OPAQUE:
                access_token = await self._create_opaque_token(
                    user_id=0,
                    client_id=client_id,
                    scope="",
                    oauth_token_db=oauth_token_db,
                )
            else:
                access_token = self._create_jwt_access_token(
                    {"id": 0, "username": "service"},
                    client_id,
                    "",
                )
            logger.info(f"Client credentials token issued for client {client_id}")
            return {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
            }

        else:
            logger.error(f"Unsupported grant_type: {grant_type}")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.unsupported_grant_type))

    async def userinfo(self, request: Request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning("Missing or invalid Authorization header in userinfo request")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, _(Message.missing_or_invalid_client_credentials))

        token = auth_header.replace("Bearer ", "")
        user_db = request.app.state.user_db
        oauth_token_db = request.app.state.oauth_token_db

        # Определяем тип токена
        if token.count('.') == 2:
            try:
                # Пробуем верифицировать JWT
                try:
                    payload = jwt.decode(token, self.public_key or self.secret_key,
                                       algorithms=[self.algorithm, "HS256"])
                except jwt.InvalidAlgorithmError:
                    payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid JWT token in userinfo: {e}")
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, _(Message.token_invalid))
            user_id = payload.get("sub")
            if not user_id:
                logger.warning("JWT payload missing 'sub'")
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, _(Message.token_invalid_payload))
            user = await user_db.get_by_id(int(user_id))
        else:
            token_record = await oauth_token_db.get_token_by_access(token)
            if not token_record or token_record.get("is_revoked"):
                logger.warning("Invalid or revoked opaque token")
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, _(Message.token_invalid))
            user = await user_db.get_by_id(token_record["user_id"])

        if not user:
            logger.error(f"User not found")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, _(Message.user_not_found))

        userinfo_data = {
            "sub": str(user["id"]),
            "name": user.get("full_name", user.get("username", "")),
            "given_name": user.get("first_name", ""),
            "family_name": user.get("last_name", ""),
            "preferred_username": user.get("username", ""),
            "email": user.get("email", ""),
            "email_verified": True,
        }
        logger.info(f"Userinfo returned for user {user['id']}")
        return userinfo_data

    async def jwks(self, request: Request):
        """Возвращает JWKS для RS256 в формате, ожидаемом GitLab."""
        if not self.public_key:
            logger.warning("No public key available, returning empty JWKS")
            return {"keys": []}

        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa

            # Загружаем публичный ключ
            public_key_obj = serialization.load_pem_public_key(
                self.public_key.encode('utf-8')
            )

            if isinstance(public_key_obj, rsa.RSAPublicKey):
                # Получаем параметры RSA ключа
                public_numbers = public_key_obj.public_numbers()

                # Формируем JWK в стандартном формате RFC 7517
                jwk_dict = {
                    "kty": "RSA",
                    "kid": "gitlab-sso-key-1",
                    "use": "sig",
                    "alg": "RS256",
                    "n": self._int_to_base64url(public_numbers.n),
                    "e": self._int_to_base64url(public_numbers.e),
                }

                logger.info(f"JWKS endpoint returning key with kid=gitlab-sso-key-1")
                return {"keys": [jwk_dict]}

        except Exception as e:
            logger.error(f"Failed to generate JWKS: {e}", exc_info=True)
            return {"keys": []}

    def _int_to_base64url(self, value: int) -> str:
        """Конвертирует integer в base64url без padding."""
        # Конвертируем integer в байты
        byte_length = (value.bit_length() + 7) // 8
        bytes_data = value.to_bytes(byte_length, byteorder='big')
        # Кодируем в base64 и удаляем padding
        return base64.urlsafe_b64encode(bytes_data).decode('utf-8').rstrip('=')

    async def openid_configuration(self, request: Request):
        base_url = settings.ISSUER.rstrip('/')
        config = {
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/authorize",
            "token_endpoint": f"{base_url}/token",
            "userinfo_endpoint": f"{base_url}/userinfo",
            "jwks_uri": f"{base_url}/jwks",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token", "client_credentials"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"] if self.algorithm == "RS256" else ["HS256"],
            "scopes_supported": ["openid", "profile", "email"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic"],
            "claims_supported": [
                "sub", "name", "given_name", "family_name",
                "preferred_username", "email", "email_verified"
            ],
        }
        logger.info(f"OpenID configuration served: {config}")
        return config

    def _create_jwt_access_token(self, user: dict, client_id: str, scope: str) -> str:
        payload = {
            "jti": str(uuid.uuid4()),
            "sub": str(user["id"]),
            "client_id": client_id,
            "scope": scope,
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "iat": datetime.now(UTC),
        }
        return jwt.encode(payload, self.private_key or self.secret_key, algorithm=self.algorithm)

    def _create_id_token(self, user: dict, client_id: str, nonce: str | None = None) -> str:
        """Создает ID Token с обязательной RS256 подписью для GitLab."""
        now = datetime.now(UTC)

        payload = {
            "iss": settings.ISSUER.rstrip('/'),
            "sub": str(user["id"]),
            "aud": client_id,
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "auth_time": int(now.timestamp()),
            "email": user.get("email", ""),
            "email_verified": True,
            "name": user.get("full_name", user.get("username", "")),
            "preferred_username": user.get("username", ""),
            "given_name": user.get("first_name", ""),
            "family_name": user.get("last_name", ""),
        }

        # Добавляем nonce, если он есть
        if nonce:
            payload["nonce"] = nonce
            logger.info(f"Adding nonce to id_token: {nonce}")

        # Удаляем None значения
        payload = {k: v for k, v in payload.items() if v is not None}

        # GitLab требует RS256 для id_token
        if self.private_key and self.algorithm == "RS256":
            # Добавляем заголовок с kid для соответствия JWKS
            headers = {
                "kid": "gitlab-sso-key-1",
                "typ": "JWT",
                "alg": "RS256"
            }
            token = jwt.encode(
                payload,
                self.private_key,
                algorithm="RS256",
                headers=headers
            )
            logger.info(f"ID Token signed with RS256, kid=gitlab-sso-key-1")

            # Само-верификация для отладки
            try:
                verified = jwt.decode(
                    token,
                    self.public_key,
                    algorithms=["RS256"],
                    audience=client_id,
                    issuer=settings.ISSUER.rstrip('/')
                )
                logger.info(f"ID Token self-verification successful for user {user['id']}")
            except Exception as e:
                logger.error(f"ID Token self-verification FAILED: {e}")

            return token
        else:
            # Fallback на HS256 (но GitLab не примет это!)
            logger.error(f"FALLBACK TO HS256 FOR ID TOKEN! GitLab will reject this!")
            token = jwt.encode(payload, self.secret_key, algorithm="HS256")
            return token

    async def _create_opaque_token(self, user_id: int, client_id: str, scope: str, oauth_token_db) -> str:
        token = secrets.token_urlsafe(32)
        return token


async def create_authorization_server():
    return OIDCServer()