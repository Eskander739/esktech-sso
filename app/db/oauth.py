"""CRUD операции для OAuth (клиенты, коды, токены) с использованием DBPool."""
from datetime import UTC, datetime, timedelta
from typing import Any

from constants import AccessTokenFormat
from db.models.auth_models import OAuthClient, OAuthCode, OAuthToken
from services.pool.db_pool import DBPool
from sqlalchemy import delete, select, update


class OAuthClientDB:
    def __init__(self, db_pool: DBPool):
        self.db_pool = db_pool

    async def get_client(self, client_id: str) -> dict[str, Any] | None:
        async with self.db_pool.get_connection() as session:
            stmt = select(OAuthClient).where(OAuthClient.client_id == client_id) # type: ignore
            result = await session.execute(stmt)
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

    async def count_active_clients(self) -> int:
        async with self.db_pool.get_connection() as session:
            stmt = select(OAuthClient).where(OAuthClient.is_active == True) # type: ignore
            result = await session.execute(stmt)
            return len(result.scalars().all())

    async def get_all_clients(self) -> list[OAuthClient]:
        async with self.db_pool.get_connection() as session:
            stmt = select(OAuthClient).where(OAuthClient.is_active == True) # type: ignore
            result = await session.execute(stmt)
            return result.scalars().all()

    async def delete_client(self, client_id: str) -> None:
        async with self.db_pool.get_connection() as session:
            stmt = delete(OAuthClient).where(OAuthClient.client_id == client_id) # type: ignore
            await session.execute(stmt)
            await session.commit()

    async def create_client(
        self,
        client_id: str,
        client_secret: str,
        redirect_uris: str,
        grant_types: str = "authorization_code refresh_token",
        response_types: str = "code",
        scope: str = "openid profile email",
        application_name: str = "",
    ) -> None:
        async with self.db_pool.get_connection() as session:
            client = OAuthClient(
                client_id=client_id,
                client_secret=client_secret,
                client_id_issued_at=datetime.now(UTC),
                redirect_uris=redirect_uris,
                grant_types=grant_types,
                response_types=response_types,
                scope=scope,
                application_name=application_name,
            )
            session.add(client)
            await session.commit()


class OAuthCodeDB:
    def __init__(self, db_pool: DBPool):
        self.db_pool = db_pool

    async def save_code(
        self,
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
        async with self.db_pool.get_connection() as session:
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

    async def get_code(self, code: str) -> dict[str, Any] | None:
        async with self.db_pool.get_connection() as session:
            stmt = select(OAuthCode).where(OAuthCode.code == code)  # type: ignore
            result = await session.execute(stmt)
            entry = result.scalar_one_or_none()
            if entry:
                expires_at = entry.expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=UTC)
                if expires_at > datetime.now(UTC):
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

    async def delete_code(self, code: str) -> None:
        async with self.db_pool.get_connection() as session:
            await session.execute(delete(OAuthCode).where(OAuthCode.code == code)) # type: ignore
            await session.commit()


class OAuthTokenDB:
    def __init__(self, db_pool: DBPool):
        self.db_pool = db_pool

    async def save_token(
        self,
        token: dict[str, Any],
        client_id: str,
        user_id: int | None,
        scope: str | None,
        refresh_token: str | None = None,
        token_type: str = AccessTokenFormat.JWT,
    ) -> None:
        expires_at = datetime.now(UTC) + timedelta(seconds=token.get("expires_in", 3600))
        async with self.db_pool.get_connection() as session:
            new_token = OAuthToken(
                client_id=client_id,
                user_id=user_id,
                token_type=token_type,
                access_token=token["access_token"],
                refresh_token=refresh_token or token.get("refresh_token"),
                scope=scope,
                expires_at=expires_at,
            )
            session.add(new_token)
            await session.commit()

    async def get_token_by_access(self, access_token: str) -> dict[str, Any] | None:
        async with self.db_pool.get_connection() as session:
            stmt = select(OAuthToken).where(OAuthToken.access_token == access_token)  # type: ignore
            result = await session.execute(stmt)
            token = result.scalar_one_or_none()
            if token and not token.is_revoked:
                expires_at = token.expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=UTC)
                if expires_at > datetime.now(UTC):
                    return {
                        "access_token": token.access_token,
                        "client_id": token.client_id,
                        "user_id": token.user_id,
                        "scope": token.scope,
                        "token_type": token.token_type,
                        "is_revoked": token.is_revoked,
                    }
            return None

    async def get_token_by_refresh(self, refresh_token: str) -> dict[str, Any] | None:
        async with self.db_pool.get_connection() as session:
            stmt = select(OAuthToken).where(OAuthToken.refresh_token == refresh_token)  # type: ignore
            result = await session.execute(stmt)
            token = result.scalar_one_or_none()
            if token and not token.is_revoked:
                expires_at = token.expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=UTC)
                if expires_at > datetime.now(UTC):
                    return {
                        "refresh_token": token.refresh_token,
                        "client_id": token.client_id,
                        "user_id": token.user_id,
                        "scope": token.scope,
                        "is_revoked": token.is_revoked,
                    }
            return None

    async def revoke_token(self, refresh_token: str) -> None:
        async with self.db_pool.get_connection() as session:
            await session.execute(
                update(OAuthToken)
                .where(OAuthToken.refresh_token == refresh_token) # type: ignore
                .values(is_revoked=True)
            )
            await session.commit()

    async def revoke_access_token(self, access_token: str) -> None:
        async with self.db_pool.get_connection() as session:
            await session.execute(
                update(OAuthToken)
                .where(OAuthToken.access_token == access_token) # type: ignore
                .values(is_revoked=True)
            )
            await session.commit()