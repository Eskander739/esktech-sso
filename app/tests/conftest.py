"""Фикстуры для тестов."""
import pytest
from db.database import Base, get_session
from httpx import AsyncClient
from main import app as main_app
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture
async def client():
    async with AsyncClient(app=main_app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
async def setup_test_db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Переопределяем зависимость
    async def override_get_session():
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            yield session
    main_app.dependency_overrides[get_session] = override_get_session
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    main_app.dependency_overrides.clear()
