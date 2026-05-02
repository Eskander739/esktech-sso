# app/services/user_service.py
"""Сервис для работы с пользователями в БД."""
from collections.abc import Sequence

from auth.password_validator import hash_password
from db.models import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class UserService:
    """CRUD операции с пользователями."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> Sequence[User]:
        """Получить всех пользователей."""
        result = await self.session.execute(select(User))
        return result.scalars().all()

    async def get_by_id(self, user_id: int) -> User | None:
        """Получить пользователя по ID."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Получить пользователя по username."""
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Получить пользователя по email."""
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, username: str, email: str, password: str, full_name: str | None = None, is_active: bool = True) -> User:
        """Создать пользователя."""
        hashed = hash_password(password) if password else None
        new_user = User(
            username=username,
            email=email,
            hashed_password=hashed,
            full_name=full_name,
            is_active=is_active,
        )
        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)
        return new_user

    async def update(self, user_id: int, email: str | None = None, password: str | None = None, full_name: str | None = None, is_active: bool | None = None) -> User | None:
        """Обновить пользователя."""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        if email is not None:
            user.email = email
        if full_name is not None:
            user.full_name = full_name
        if is_active is not None:
            user.is_active = is_active
        if password:
            user.hashed_password = hash_password(password)

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete(self, user_id: int) -> bool:
        """Удалить пользователя."""
        user = await self.get_by_id(user_id)
        if not user:
            return False
        await self.session.delete(user)
        await self.session.commit()
        return True

    async def check_exists(self, username: str, email: str, exclude_id: int | None = None) -> tuple[bool, bool]:
        """Проверить существование username и email."""
        username_exists = await self.get_by_username(username) is not None
        if exclude_id:
            email_user = await self.get_by_email(email)
            email_exists = email_user is not None and email_user.id != exclude_id
        else:
            email_exists = await self.get_by_email(email) is not None
        return username_exists, email_exists