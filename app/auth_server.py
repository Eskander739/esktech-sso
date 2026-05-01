"""Настройка OIDC-сервера на основе Authlib."""
from collections.abc import Coroutine
from typing import Any

from authlib.oauth2 import AuthorizationServer as StarletteAuthorizationServer
from authlib.oauth2.rfc6749 import grants
from authlib.oauth2.rfc6749.requests import OAuth2Request
from authlib.oauth2.rfc7636 import CodeChallenge
from db.crud import (
    delete_authorization_code,
    get_authorization_code,
    get_oauth_client,
    get_token,
    get_user_by_id,
    revoke_token,
    save_authorization_code,
)
from db.models import OAuthClient as OAuthClientModel


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    """Авторизационный код грант с PKCE."""

    async def authenticate_user(self, authorization_code: str) -> Coroutine[Any, Any, dict[str, Any] | None] | None:
        """По коду получить пользователя."""
        code_data = await get_authorization_code(authorization_code)
        if not code_data:
            return None
        user = get_user_by_id(code_data["user_id"])
        if not user:
            return None
        await delete_authorization_code(authorization_code)
        return user

    def save_authorization_code(self, code: str, request: OAuth2Request) -> None:
        """Сохранить код авторизации."""
        save_authorization_code(
            code=code,
            client_id=request.client.client_id,
            redirect_uri=request.redirect_uri,
            user_id=request.user["id"],
            scope=request.scope,
            nonce=request.data.get("nonce"),
            code_challenge=request.data.get("code_challenge"),
            code_challenge_method=request.data.get("code_challenge_method"),
        )


class RefreshTokenGrant(grants.RefreshTokenGrant):
    """Грант обновления токена."""

    async def authenticate_refresh_token(self, refresh_token: str) -> Coroutine[Any, Any, dict[str, Any] | None] | None:
        """Проверить refresh token."""
        token = await get_token(refresh_token=refresh_token)
        if not token or token["is_revoked"]:
            return None
        return token

    async def revoke_old_credential(self, credential: dict[str, Any]) -> None:
        """Отозвать старый refresh token."""
        await revoke_token(credential["refresh_token"])


class PasswordGrant(grants.ResourceOwnerPasswordCredentialsGrant):
    """Грант пароль (для OAuth2, не OIDC)."""

    async def authenticate_user(self, username: str, password: str) -> dict[str, Any] | None:
        from auth.user_source import authenticate_user  # избегаем циклического импорта
        user = await authenticate_user(username, password)
        return user


class ClientCredentialsGrant(grants.ClientCredentialsGrant):
    """Грант учётных данных клиента."""

    @staticmethod
    def authenticate_client(request: OAuth2Request) -> bool:
        return request.client is not None


async def create_authorization_server():
    """Фабрика OIDC-сервера."""
    server = StarletteAuthorizationServer()
    server.register_grant(AuthorizationCodeGrant, [CodeChallenge(required=True)])
    server.register_grant(RefreshTokenGrant)
    server.register_grant(PasswordGrant)
    server.register_grant(ClientCredentialsGrant)

    # Функция загрузки OAuth клиента по client_id
    async def query_client(client_id: str):
        client = await get_oauth_client(client_id)
        if client:
            return OAuthClientModel(
                client_id=client["client_id"],
                client_secret=client["client_secret"],
                client_id_issued_at=client["client_id_issued_at"],
                client_secret_expires_at=client.get("client_secret_expires_at", 0),
                redirect_uris=client["redirect_uris"],
                grant_types=client.get("grant_types"),
                response_types=client.get("response_types"),
                scope=client.get("scope"),
                token_endpoint_auth_method=client.get("token_endpoint_auth_method", "client_secret_basic"),
            )
        return None

    server.query_client = query_client

    def save_token(token: dict[str, Any], request: OAuth2Request) -> None:
        server.save_token(token, request)

    server.save_token = save_token

    return server
