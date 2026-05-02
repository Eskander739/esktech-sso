"""Фикстуры для тестов."""
import asyncio
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from auth.password_validator import hash_password
from auth_server import create_authorization_server
from config import settings
from db.oauth import OAuthClientDB, OAuthCodeDB, OAuthTokenDB
from db.users import UserDB
from httpx import ASGITransport, AsyncClient
from main import app
from services.db_pool import DBPool
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Используем PostgreSQL для тестов (отдельная БД)
TEST_DATABASE_URL = "postgresql+asyncpg://sso_user:sso_pass@localhost:5432/sso"
settings.DATABASE_URL = TEST_DATABASE_URL


@pytest.fixture(autouse=True, scope="function")
async def setup_test_db():
    """Настройка тестовой БД для каждого теста с очисткой данных."""
    db_pool = DBPool()
    await db_pool.create_tables()

    # Очищаем все таблицы перед тестом
    async with db_pool.get_connection() as session:
        try:
            # Очищаем таблицы в правильном порядке (сначала зависимые)
            await session.execute(text("TRUNCATE TABLE oauth_tokens CASCADE"))
            await session.execute(text("TRUNCATE TABLE oauth_codes CASCADE"))
            await session.execute(text("TRUNCATE TABLE oauth_clients CASCADE"))
            await session.execute(text("TRUNCATE TABLE users CASCADE"))
            await session.commit()
        except SQLAlchemyError as e:
            print("Error truncating tables: %s", e)
            await session.rollback()

    app.state.db_pool = db_pool
    app.state.oauth_client_db = OAuthClientDB(db_pool)
    app.state.oauth_code_db = OAuthCodeDB(db_pool)
    app.state.oauth_token_db = OAuthTokenDB(db_pool)
    app.state.user_db = UserDB(db_pool)
    app.state.oidc_server = await create_authorization_server()

    yield

    # Очистка после теста
    await db_pool.close_pool()

    # Удаляем атрибуты из app.state
    if hasattr(app.state, 'db_pool'):
        delattr(app.state, 'db_pool')
    if hasattr(app.state, 'oauth_client_db'):
        delattr(app.state, 'oauth_client_db')
    if hasattr(app.state, 'oauth_code_db'):
        delattr(app.state, 'oauth_code_db')
    if hasattr(app.state, 'oauth_token_db'):
        delattr(app.state, 'oauth_token_db')
    if hasattr(app.state, 'user_db'):
        delattr(app.state, 'user_db')
    if hasattr(app.state, 'oidc_server'):
        delattr(app.state, 'oidc_server')


@pytest.fixture
async def client():
    """HTTP клиент для тестов."""
    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def test_user():
    """Создаёт тестового пользователя в БД."""
    user_db = app.state.user_db
    hashed = hash_password("testpass123")
    user_id = await user_db.create(
        username="testuser",
        email="test@example.com",
        hashed_password=hashed,
        full_name="Test User",
        is_active=True
    )
    user = await user_db.get_by_id(user_id)
    return user


@pytest.fixture
async def test_client_app():
    """Создаёт тестового OAuth2 клиента."""
    client_db = app.state.oauth_client_db
    client_id = "test_client"
    client_secret = "test_secret"
    await client_db.create_client(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uris="http://localhost:8000/callback",
        grant_types="authorization_code refresh_token password",
        response_types="code",
        scope="openid profile email",
        application_name="Test Client"
    )
    return {"client_id": client_id, "client_secret": client_secret}


@pytest.fixture
async def auth_token(test_user, test_client_app):
    """Возвращает access token для тестового пользователя."""
    server = app.state.oidc_server
    token = server._create_access_token(
        user=test_user,
        client_id=test_client_app["client_id"],
        scope="openid profile email"
    )
    return token


@pytest.fixture
async def expired_token(test_user, test_client_app):
    """Возвращает просроченный access token."""
    server = app.state.oidc_server
    payload = {
        "sub": str(test_user["id"]),
        "client_id": test_client_app["client_id"],
        "scope": "openid",
        "exp": datetime.now(UTC) - timedelta(hours=1),
        "iat": datetime.now(UTC) - timedelta(hours=2),
    }
    token = jwt.encode(payload, server.secret_key, algorithm=server.algorithm)
    return token


@pytest.fixture(scope="session")
def ldap_test_server():
    """Запускает тестовый LDAP сервер."""

    # Здесь нужно настроить тестовый LDAP сервер
    # Например, используя ldap3 или запуская docker контейнер

    # Вариант 1: Использовать мок
    class MockLDAPServer:
        def __init__(self):
            self.users = {
                "ldap_user": "correct_password",
                "new_ldap_user": "password123"
            }

        def authenticate(self, username, password):
            return self.users.get(username) == password

    server = MockLDAPServer()
    yield server
    # Закрываем сервер если нужно