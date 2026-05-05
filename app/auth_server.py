"""Настройка OIDC-сервера на основе Authlib."""
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from config import settings
from constants import AccessTokenFormat, GrantType
from fastapi import HTTPException, Request, status
from models.msg import Message
from services.localization import _
from starlette.datastructures import UploadFile
from starlette.responses import RedirectResponse


class OIDCServer:
    """Простой OIDC сервер, поддерживающий JWT и OPAQUE токены."""

    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"

    async def authorize(
        self,
        request: Request,
        client_id: str,
        redirect_uri: str,
        response_type: str,
        scope: str,
        state: str | None = None,
    ):
        oauth_client_db = request.app.state.oauth_client_db
        oauth_code_db = request.app.state.oauth_code_db

        client = await oauth_client_db.get_client(client_id)
        if not client or not client.get("is_active"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.invalid_client))

        allowed_uris = client.get("redirect_uris", "").split()
        if redirect_uri not in allowed_uris:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.invalid_redirect_uri))

        if response_type != "code":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.only_authorization_code_flow_is_supported))

        user = request.session.get("user")
        if not user:
            request.session["oauth_params"] = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "state": state,
            }
            return RedirectResponse(url="/login")

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

        redirect_url = f"{redirect_uri}?code={code}"
        if state:
            redirect_url += f"&state={state}"
        return RedirectResponse(url=redirect_url)

    async def token(self, request: Request):
        form = await request.form()
        grant_type = form.get("grant_type")
        client_id = form.get("client_id")
        client_secret = form.get("client_secret")

        if not isinstance(grant_type, str) or not isinstance(client_id, str) or not isinstance(client_secret, str):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.invalid_ot_missing_form_parameters))

        oauth_client_db = request.app.state.oauth_client_db
        oauth_code_db = request.app.state.oauth_code_db
        oauth_token_db = request.app.state.oauth_token_db
        user_db = request.app.state.user_db

        client = await oauth_client_db.get_client(client_id)
        if not client or not client.get("is_active"):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, _(Message.invalid_client))

        if client.get("client_secret") != client_secret:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, _(Message.invalid_client_secret))

        # Определяем формат токена из настроек
        token_format = settings.ACCESS_TOKEN_FORMAT

        if grant_type == GrantType.AUTHORIZATION_CODE:
            code = form.get("code")
            redirect_uri = form.get("redirect_uri")
            if not isinstance(code, str) or not isinstance(redirect_uri, str):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.invalid_or_missing_code_or_redirect_uri))

            code_data = await oauth_code_db.get_code(code)
            if not code_data:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.invalid_or_expired_code))

            if code_data["client_id"] != client_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.code_client_mismath))
            if code_data["redirect_uri"] != redirect_uri:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.redirect_uri_mismath))

            user = await user_db.get_by_id(code_data["user_id"])
            if not user:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.user_not_found))

            await oauth_code_db.delete_code(code)

            # Генерация токенов
            if token_format == AccessTokenFormat.OPAQUE:
                access_token = await self._create_opaque_token(
                    user_id=user["id"],
                    client_id=client_id,
                    scope=code_data["scope"],
                    oauth_token_db=oauth_token_db,
                )
                refresh_token: str | None | UploadFile = secrets.token_urlsafe(32)
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

            id_token = self._create_id_token(user, client_id)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "id_token": id_token,
                "token_type": "Bearer",
                "expires_in": 3600,
            }

        elif grant_type == GrantType.REFRESH_TOKEN:
            refresh_token = form.get(GrantType.REFRESH_TOKEN)
            if not isinstance(refresh_token, str):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.refresh_token_invalid_or_missing))

            token_data = await oauth_token_db.get_token_by_refresh(refresh_token)
            if not token_data or token_data.get("is_revoked"):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.refresh_token_invalid))

            if token_data["client_id"] != client_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.client_mismath))

            user = await user_db.get_by_id(token_data["user_id"])
            if not user:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.user_not_found))

            # Отзываем старый токен
            await oauth_token_db.revoke_token(refresh_token)

            # Новые токены
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
            return {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
            }

        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _(Message.unsupported_grant_type))

    async def userinfo(self, request: Request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, _(Message.missing_or_invalid_client_credentials))

        token = auth_header.replace("Bearer ", "")
        user_db = request.app.state.user_db
        oauth_token_db = request.app.state.oauth_token_db

        # Определяем тип токена по формату: JWT содержит две точки, OPAQUE — нет
        if token.count('.') == 2:
            # JWT
            try:
                payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            except jwt.InvalidTokenError:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, _(Message.token_invalid))
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, _(Message.token_invalid_payload))
            user = await user_db.get_by_id(int(user_id))
            if not user:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, _(Message.user_not_found))
        else:
            # OPAQUE token
            token_record = await oauth_token_db.get_token_by_access(token)
            if not token_record or token_record.get("is_revoked"):
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, _(Message.token_invalid))
            user = await user_db.get_by_id(token_record["user_id"])
            if not user:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, _(Message.user_not_found))

        return {
            "sub": str(user["id"]),
            "username": user.get("username", ""),
            "email": user.get("email", ""),
            "preferred_username": user.get("username", ""),
        }

    async def jwks(self, request: Request):
        return {"keys": []}

    async def openid_configuration(self, request: Request):
        return {
            "issuer": settings.ISSUER,
            "authorization_endpoint": f"{settings.ISSUER}/authorize",
            "token_endpoint": f"{settings.ISSUER}/token",
            "userinfo_endpoint": f"{settings.ISSUER}/userinfo",
            "jwks_uri": f"{settings.ISSUER}/jwks",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token", "client_credentials"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["HS256"],
        }

    def _create_jwt_access_token(self, user: dict, client_id: str, scope: str) -> str:
        payload = {
            "jti": str(uuid.uuid4()),  # уникальный идентификатор токена
            "sub": str(user["id"]),
            "client_id": client_id,
            "scope": scope,
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "iat": datetime.now(UTC),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def _create_id_token(self, user: dict, client_id: str) -> str:
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

    async def _create_opaque_token(
        self, user_id: int, client_id: str, scope: str, oauth_token_db
    ) -> str:
        token = secrets.token_urlsafe(32)
        # Не сохраняем сразу, только возвращаем токен; сохранение делает вызывающий код.
        # Но нам нужно убедиться, что токен уникален.
        # Вызывающий код сам вызовет save_token. Здесь просто генерируем.
        return token


async def create_authorization_server():
    return OIDCServer()