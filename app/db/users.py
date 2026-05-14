from typing import Any

from config import settings
from constants import AccessTokenFormat, UserRole
from db.models.user_models import UserModel
from services.pool.db_pool import DBPool
from sqlalchemy import delete, select, update


class UserDB:
    def __init__(self, db_pool: DBPool):
        self.db_pool = db_pool

    @staticmethod
    def _user_to_dict(user: UserModel) -> dict[str, Any]:
        return {
            "id": user.id,
            "uuid": str(user.uuid),
            "token_type": user.token_type,
            "role": user.role,
            "username": user.username,
            "email": user.email,
            "hashed_password": user.hashed_password,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }

    async def get_by_username(self, username: str) -> dict[str, Any] | None:
        async with self.db_pool.get_connection() as session:
            stmt = select(UserModel).where(UserModel.username == username) # type: ignore
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            return self._user_to_dict(user) if user else None

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        async with self.db_pool.get_connection() as session:
            stmt = select(UserModel).where(UserModel.email == email) # type: ignore
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            return self._user_to_dict(user) if user else None

    async def get_by_id(self, user_id: int) -> dict[str, Any] | None:
        async with self.db_pool.get_connection() as session:
            stmt = select(UserModel).where(UserModel.id == user_id) # type: ignore
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            return self._user_to_dict(user) if user else None

    async def get_all(self) -> list[dict[str, Any]]:
        async with self.db_pool.get_connection() as session:
            stmt = select(UserModel)
            result = await session.execute(stmt)
            users = result.scalars().all()
            return [self._user_to_dict(u) for u in users]

    async def create(
        self,
        username: str,
        email: str,
        hashed_password: str | None = None,
        full_name: str = "",
        is_active: bool = True,
        token_type: AccessTokenFormat = settings.ACCESS_TOKEN_FORMAT,
        role: UserRole = UserRole.USER,
    ) -> int:
        async with self.db_pool.get_connection() as session:
            user = UserModel(
                username=username,
                email=email,
                hashed_password=hashed_password,
                full_name=full_name,
                is_active=is_active,
                token_type=token_type,
                role=role,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user.id

    async def update_email(self, user_id: int, email: str) -> None:
        async with self.db_pool.get_connection() as session:
            stmt = update(UserModel).where(UserModel.id == user_id).values(email=email) # type: ignore
            await session.execute(stmt)
            await session.commit()

    async def update_full_name(self, user_id: int, full_name: str) -> None:
        async with self.db_pool.get_connection() as session:
            stmt = update(UserModel).where(UserModel.id == user_id).values(full_name=full_name) # type: ignore
            await session.execute(stmt)
            await session.commit()

    async def update_is_active(self, user_id: int, is_active: bool) -> None:
        async with self.db_pool.get_connection() as session:
            stmt = update(UserModel).where(UserModel.id == user_id).values(is_active=is_active) # type: ignore
            await session.execute(stmt)
            await session.commit()

    async def update_password(self, user_id: int, hashed_password: str) -> None:
        async with self.db_pool.get_connection() as session:
            stmt = update(UserModel).where(UserModel.id == user_id).values(hashed_password=hashed_password) # type: ignore
            await session.execute(stmt)
            await session.commit()

    async def delete(self, user_id: int) -> None:
        async with self.db_pool.get_connection() as session:
            stmt = delete(UserModel).where(UserModel.id == user_id) # type: ignore
            await session.execute(stmt)
            await session.commit()