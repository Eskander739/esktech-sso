"""Настройка OIDC-сервера на основе Authlib."""
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from config import settings
from fastapi import HTTPException, Request, status
from starlette.datastructures import UploadFile
from starlette.responses import RedirectResponse

# Секретный ключ для JWT (в реальном приложении брать из переменных окружения)
SECRET_KEY = "your-super-secret-key-minimum-32-characters"
ALGORITHM = "HS256"


class OIDCServer:
    """Простой OIDC сервер, использующий зависимости из request.app.state."""

    def __init__(self):
        self.secret_key = SECRET_KEY
        self.algorithm = ALGORITHM

    async def authorize(
        self,
        request: Request,
        client_id: str,
        redirect_uri: str,
        response_type: str,
        scope: str,
        state: str | None = None,
    ):
        """Эндпоинт авторизации."""
        # Получаем зависимости из state
        oauth_client_db = request.app.state.oauth_client_db
        oauth_code_db = request.app.state.oauth_code_db

        # Проверяем клиента
        client = await oauth_client_db.get_client(client_id)
        if not client or not client.get("is_active"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid client")

        # Проверяем redirect_uri
        allowed_uris = client.get("redirect_uris", "").split()
        if redirect_uri not in allowed_uris:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid redirect_uri")

        # Проверяем response_type
        if response_type != "code":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only authorization_code flow is supported")

        user = request.session.get("user")
        if not user:
            # Сохраняем параметры и отправляем на логин
            request.session["oauth_params"] = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "state": state,
            }
            return RedirectResponse(url="/oidc/login")

        # Генерируем код
        code = secrets.token_urlsafe(32)
        await oauth_code_db.save_code(
            code=code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            user_id=user["id"],
            scope=scope,
            nonce=None,
            code_challenge=None,
            code_challenge_method=None,
        )

        # Редирект обратно с кодом
        redirect_url = f"{redirect_uri}?code={code}"
        if state:
            redirect_url += f"&state={state}"

        return RedirectResponse(url=redirect_url)

    async def token(self, request: Request):
        """Токен эндпоинт."""
        form = await request.form()
        grant_type = form.get("grant_type")
        client_id = form.get("client_id")
        client_secret = form.get("client_secret")

        # Проверяем, что обязательные параметры являются строками
        if not isinstance(grant_type, str) or not isinstance(client_id, str) or not isinstance(client_secret, str):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or missing form parameters")

        # Получаем зависимости из state
        oauth_client_db = request.app.state.oauth_client_db
        oauth_code_db = request.app.state.oauth_code_db
        oauth_token_db = request.app.state.oauth_token_db
        user_db = request.app.state.user_db

        # Проверяем клиента
        client = await oauth_client_db.get_client(client_id)
        if not client or not client.get("is_active"):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid client")

        if client.get("client_secret") != client_secret:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid client secret")

        if grant_type == "authorization_code":
            code = form.get("code")
            redirect_uri = form.get("redirect_uri")

            if not isinstance(code, str) or not isinstance(redirect_uri, str):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or missing code/redirect_uri")

            # Проверяем код
            code_data = await oauth_code_db.get_code(code)
            if not code_data:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid code")

            if code_data["client_id"] != client_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Code client mismatch")

            if code_data["redirect_uri"] != redirect_uri:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Redirect URI mismatch")

            user = await user_db.get_by_id(code_data["user_id"])
            if not user:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "User not found")

            # Удаляем использованный код
            await oauth_code_db.delete_code(code)

            # Генерируем токены (теперь client_id гарантированно str)
            access_token = self._create_access_token(user, client_id, code_data["scope"])
            refresh_token: str | None | UploadFile = secrets.token_urlsafe(32)
            id_token = self._create_id_token(user, client_id)

            # Сохраняем токен
            await oauth_token_db.save_token(
                token={
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expires_in": 3600,
                },
                client_id=client_id,
                user_id=user["id"],
                scope=code_data["scope"],
            )

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "id_token": id_token,
                "token_type": "Bearer",
                "expires_in": 3600,
            }

        elif grant_type == "refresh_token":
            refresh_token = form.get("refresh_token")

            if not isinstance(refresh_token, str):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or missing refresh_token")

            token_data = await oauth_token_db.get_token_by_refresh(refresh_token)
            if not token_data or token_data.get("is_revoked"):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid refresh token")

            if token_data["client_id"] != client_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Client mismatch")

            user = await user_db.get_by_id(token_data["user_id"])
            if not user:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "User not found")

            # Удаляем старый токен
            await oauth_token_db.revoke_token(refresh_token)

            # Генерируем новые токены
            new_access_token = self._create_access_token(user, client_id, token_data["scope"])
            new_refresh_token = secrets.token_urlsafe(32)

            # Уникальный суффикс для access token
            unique_suffix = secrets.token_hex(8)
            new_access_token = f"{new_access_token}_{unique_suffix}"

            await oauth_token_db.save_token(
                token={"access_token": new_access_token, "expires_in": 3600},
                client_id=client_id,
                user_id=user["id"],
                scope=token_data["scope"],
                refresh_token=new_refresh_token,
            )

            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "Bearer",
                "expires_in": 3600,
            }

        elif grant_type == "client_credentials":
            # Для сервисных аккаунтов
            access_token = self._create_access_token(
                {"id": 0, "username": "service"},
                client_id,
                "",
            )
            return {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
            }

        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported grant_type")

    async def userinfo(self, request: Request):
        """Userinfo эндпоинт."""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid token")

        token = auth_header.replace("Bearer ", "")

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.InvalidTokenError:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token payload")

        user_db = request.app.state.user_db
        user = await user_db.get_by_id(int(user_id))
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

        return {
            "sub": str(user["id"]),
            "username": user.get("username", ""),
            "email": user.get("email", ""),
            "preferred_username": user.get("username", ""),
        }

    async def jwks(self, request: Request):
        """JWKS эндпоинт."""
        # Для HS256 ключи не публикуются, но эндпоинт должен существовать
        return {"keys": []}

    async def openid_configuration(self, request: Request):
        """Discovery эндпоинт."""
        return {
            "issuer": settings.ISSUER,
            "authorization_endpoint": f"{settings.ISSUER}/oidc/authorize",
            "token_endpoint": f"{settings.ISSUER}/oidc/token",
            "userinfo_endpoint": f"{settings.ISSUER}/oidc/userinfo",
            "jwks_uri": f"{settings.ISSUER}/oidc/jwks",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token", "client_credentials"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["HS256"],
        }

    def _create_access_token(self, user: dict, client_id: str, scope: str) -> str:
        """Создание access token."""
        payload = {
            "sub": str(user["id"]),
            "client_id": client_id,
            "scope": scope,
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "iat": datetime.now(UTC),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def _create_id_token(self, user: dict, client_id: str) -> str:
        """Создание ID token."""
        payload = {
            "iss": settings.ISSUER,
            "sub": str(user["id"]),
            "aud": client_id,
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "iat": datetime.now(UTC),
            "email": user.get("email", ""),
            "preferred_username": user.get("username", ""),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)


async def create_authorization_server():
    """Создание OIDC сервера."""
    return OIDCServer()
