"""Подключение к базе данных."""
from collections.abc import AsyncGenerator

from config import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()


async def init_db() -> None:
    """Создание таблиц при старте (для dev)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Закрытие соединения."""
    await engine.dispose()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Генератор сессий для зависимостей FastAPI."""
    async with async_session_maker() as session:
        yield session
