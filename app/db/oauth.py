"""CRUD операции для OAuth (клиенты, коды, токены) с использованием DBPool."""
from datetime import UTC, datetime, timedelta
from typing import Any

from constants import AccessTokenFormat
from db.models.auth_models import OAuthClientModel, OAuthCodeModel, OAuthTokenModel
from services.pool.db_pool import DBPool
from sqlalchemy import delete, select, update


class OAuthClientDB:
    def __init__(self, db_pool: DBPool):
        self.db_pool = db_pool

    async def get_client_by_client_id(self, client_id: str) -> dict[str, Any] | None:
        async with self.db_pool.get_connection() as session:
            stmt = select(OAuthClientModel).where(OAuthClientModel.client_id == client_id) # type: ignore
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

    async def get_client_by_id(self, client_id: int) -> dict[str, Any] | None:
        async with self.db_pool.get_connection() as session:
            stmt = select(OAuthClientModel).where(OAuthClientModel.id == int(client_id)) # type: ignore
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
            stmt = select(OAuthClientModel).where(OAuthClientModel.is_active == True) # type: ignore
            result = await session.execute(stmt)
            return len(result.scalars().all())

    async def get_all_clients(self) -> list[OAuthClientModel]:
        async with self.db_pool.get_connection() as session:
            stmt = select(OAuthClientModel).where(OAuthClientModel.is_active == True) # type: ignore
            result = await session.execute(stmt)
            return result.scalars().all()

    async def delete_client_by_id(self, client_id: int) -> None:
        async with self.db_pool.get_connection() as session:
            stmt = delete(OAuthClientModel).where(OAuthClientModel.id == int(client_id)) # type: ignore
            await session.execute(stmt)
            await session.commit()

    async def delete_client_by_client_id(self, client_id: str) -> None:
        async with self.db_pool.get_connection() as session:
            stmt = delete(OAuthClientModel).where(OAuthClientModel.client_id == client_id) # type: ignore
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
            client = OAuthClientModel(
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
            oauth_code = OAuthCodeModel(
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
            stmt = select(OAuthCodeModel).where(OAuthCodeModel.code == code)  # type: ignore
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
            await session.execute(delete(OAuthCodeModel).where(OAuthCodeModel.code == code)) # type: ignore
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
            new_token = OAuthTokenModel(
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
            stmt = select(OAuthTokenModel).where(OAuthTokenModel.access_token == access_token)  # type: ignore
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
            stmt = select(OAuthTokenModel).where(OAuthTokenModel.refresh_token == refresh_token)  # type: ignore
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
                        "role": token.role,
                        "scope": token.scope,
                        "is_revoked": token.is_revoked,
                    }
            return None

    async def revoke_token(self, refresh_token: str) -> None:
        async with self.db_pool.get_connection() as session:
            await session.execute(
                update(OAuthTokenModel)
                .where(OAuthTokenModel.refresh_token == refresh_token) # type: ignore
                .values(is_revoked=True)
            )
            await session.commit()

    async def revoke_access_token(self, access_token: str) -> None:
        async with self.db_pool.get_connection() as session:
            await session.execute(
                update(OAuthTokenModel)
                .where(OAuthTokenModel.access_token == access_token) # type: ignore
                .values(is_revoked=True)
            )
            await session.commit()

    async def revoke_all_user_tokens(
            self,
            user_id: int,
            exclude_access_token: str | None = None,
            reason: str = "user_logout"
    ) -> int:
        """Отозвать ВСЕ токены пользователя (при логауте или смене пароля)"""
        async with self.db_pool.get_connection() as session:
            stmt = select(OAuthTokenModel).where(
                OAuthTokenModel.user_id == user_id,
                OAuthTokenModel.is_revoked == False
            )
            result = await session.execute(stmt)
            tokens = result.scalars().all()

            revoked_count = 0
            for token in tokens:
                # Исключаем текущий токен, если нужно
                if exclude_access_token and token.access_token == exclude_access_token:
                    continue

                token.is_revoked = True
                revoked_count += 1

            if revoked_count > 0:
                await session.commit()

            return revoked_count

    async def revoke_all_client_tokens(
            self,
            client_id: str,
            reason: str = "client_deleted"
    ) -> int:
        """Отозвать все токены конкретного клиента (при удалении клиента)"""
        async with self.db_pool.get_connection() as session:
            stmt = select(OAuthTokenModel).where(
                OAuthTokenModel.client_id == client_id,
                OAuthTokenModel.is_revoked == False
            )
            result = await session.execute(stmt)
            tokens = result.scalars().all()

            for token in tokens:
                token.is_revoked = True

            await session.commit()
            return len(tokens)

    async def revoke_expired_tokens(self) -> int:
        """Отозвать все просроченные токены (для фоновой задачи)"""
        async with self.db_pool.get_connection() as session:
            stmt = select(OAuthTokenModel).where(
                OAuthTokenModel.expires_at < datetime.now(UTC),
                OAuthTokenModel.is_revoked == False
            )
            result = await session.execute(stmt)
            tokens = result.scalars().all()

            for token in tokens:
                token.is_revoked = True

            await session.commit()
            return len(tokens)

    async def get_user_active_tokens(self, user_id: int) -> list[dict]:
        """Получить все активные токены пользователя"""
        async with self.db_pool.get_connection() as session:
            stmt = select(OAuthTokenModel).where(
                OAuthTokenModel.user_id == user_id,
                OAuthTokenModel.is_revoked == False,
                OAuthTokenModel.expires_at > datetime.now(UTC)
            )
            result = await session.execute(stmt)
            tokens = result.scalars().all()

            return [
                {
                    "token_type": t.token_type,
                    "client_id": t.client_id,
                    "scope": t.scope,
                    "expires_at": t.expires_at,
                    "issued_at": t.issued_at
                }
                for t in tokens
            ]

    async def cleanup_old_revoked_tokens(self, days_old: int = 30) -> int:
        """Удалить старые отозванные токены из БД"""
        async with self.db_pool.get_connection() as session:
            cutoff_date = datetime.now(UTC) - timedelta(days=days_old)
            stmt = delete(OAuthTokenModel).where(
                OAuthTokenModel.is_revoked == True,
                OAuthTokenModel.issued_at < cutoff_date
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount