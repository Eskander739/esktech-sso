"""CRUD операции с БД (синхронные/асинхронные обёртки)."""
from datetime import UTC, datetime, timedelta
from typing import Any

from db.database import async_session_maker
from db.models import OAuthClient, OAuthCode, OAuthToken, User
from sqlalchemy import delete, select


# Пользователи
async def get_user_by_username(username: str) -> dict[str, Any] | None:
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.username == username)) # type: ignore
        user = result.scalar_one_or_none()
        if user:
            return {
                "id": user.id,
                "uuid": str(user.uuid),
                "username": user.username,
                "email": user.email,
                "hashed_password": user.hashed_password,
                "full_name": user.full_name,
                "is_active": user.is_active,
            }
        return None


async def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == user_id)) # type: ignore
        user = result.scalar_one_or_none()
        if user:
            return {
                "id": user.id,
                "uuid": str(user.uuid),
                "username": user.username,
                "email": user.email,
                "hashed_password": user.hashed_password,
                "full_name": user.full_name,
                "is_active": user.is_active,
            }
        return None


async def create_user(username: str, email: str, hashed_password: str | None = None, full_name: str = "") -> int:
    async with async_session_maker() as session:
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        return user.id


# OAuth клиенты
async def get_oauth_client(client_id: str) -> dict[str, Any] | None:
    async with async_session_maker() as session:
        result = await session.execute(select(OAuthClient).where(OAuthClient.client_id == client_id)) # type: ignore
        client = result.scalar_one_or_none()
        if client:
            return {
                "client_id": client.client_id,
                "client_secret": client.client_secret,
                "client_id_issued_at": client.client_id_issued_at,
                "client_secret_expires_at": client.client_secret_expires_at,
                "redirect_uris": client.redirect_uris,
                "grant_types": client.grant_types,
                "response_types": client.response_types,
                "scope": client.scope,
                "token_endpoint_auth_method": client.token_endpoint_auth_method,
                "is_active": client.is_active,
            }
        return None


async def count_oauth_clients() -> int:
    async with async_session_maker() as session:
        result = await session.execute(select(OAuthClient).where(OAuthClient.is_active == True)) # type: ignore
        return len(result.scalars().all())


async def create_oauth_client(
    client_id: str,
    client_secret: str,
    redirect_uris: str,
    grant_types: str = "authorization_code refresh_token",
    response_types: str = "code",
    scope: str = "openid profile email",
    application_name: str = "",
) -> None:
    async with async_session_maker() as session:
        client = OAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uris=redirect_uris,
            grant_types=grant_types,
            response_types=response_types,
            scope=scope,
            application_name=application_name,
        )
        session.add(client)
        await session.commit()


# Коды авторизации
async def save_authorization_code(
    code: str,
    client_id: str,
    redirect_uri: str,
    user_id: int,
    scope: str,
    nonce: str | None,
    code_challenge: str | None,
    code_challenge_method: str | None,
) -> None:
    expires_at = datetime.now(UTC) + timedelta(minutes=10)
    async with async_session_maker() as session:
        oauth_code = OAuthCode(
            code=code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            user_id=user_id,
            scope=scope,
            nonce=nonce,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            expires_at=expires_at,
        )
        session.add(oauth_code)
        await session.commit()


async def get_authorization_code(code: str) -> dict[str, Any] | None:
    async with async_session_maker() as session:
        result = await session.execute(select(OAuthCode).where(OAuthCode.code == code)) # type: ignore
        entry = result.scalar_one_or_none()
        if entry and entry.expires_at > datetime.now(UTC):
            return {
                "code": entry.code,
                "client_id": entry.client_id,
                "redirect_uri": entry.redirect_uri,
                "user_id": entry.user_id,
                "scope": entry.scope,
                "nonce": entry.nonce,
                "code_challenge": entry.code_challenge,
                "code_challenge_method": entry.code_challenge_method,
            }
        return None


async def delete_authorization_code(code: str) -> None:
    async with async_session_maker() as session:
        await session.execute(delete(OAuthCode).where(OAuthCode.code == code)) # type: ignore
        await session.commit()


# Токены
async def save_token(token: dict[str, Any], client_id: str, user_id: int | None, scope: str | None) -> None:
    expires_at = datetime.now(UTC) + timedelta(seconds=token.get("expires_in", 3600))
    async with async_session_maker() as session:
        # Удаляем старые токены для этого клиента+пользователя (опционально)
        new_token = OAuthToken(
            client_id=client_id,
            user_id=user_id,
            access_token=token["access_token"],
            refresh_token=token.get("refresh_token"),
            scope=scope,
            expires_at=expires_at,
        )
        session.add(new_token)
        await session.commit()


async def get_token(refresh_token: str) -> dict[str, Any] | None:
    async with async_session_maker() as session:
        result = await session.execute(
            select(OAuthToken).where(OAuthToken.refresh_token == refresh_token) # type: ignore
        )
        token = result.scalar_one_or_none()
        if token and not token.is_revoked:
            return {
                "refresh_token": token.refresh_token,
                "client_id": token.client_id,
                "user_id": token.user_id,
                "scope": token.scope,
                "is_revoked": token.is_revoked,
            }
        return None


async def revoke_token(refresh_token: str) -> None:
    async with async_session_maker() as session:
        await session.execute(
            delete(OAuthToken).where(OAuthToken.refresh_token == refresh_token) # type: ignore
        )
        await session.commit()
