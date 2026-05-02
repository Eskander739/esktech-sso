"""Фикстуры для тестов."""
import time
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from auth.password_validator import hash_password
from auth_server import create_authorization_server
from config import settings
from db.oauth import OAuthClientDB, OAuthCodeDB, OAuthTokenDB
from db.users import UserDB
from httpx import ASGITransport, AsyncClient
from ldap3 import ALL, Connection, Server
from main import app
from services.db_pool import DBPool
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from utils.cli import CLIControl

settings.DATABASE_URL = "postgresql+asyncpg://sso_user:sso_pass@localhost:5432/sso"

# Конфигурация тестового LDAP
LDAP_CONTAINER_NAME = "test-ldap-server"
LDAP_PORT = 389
LDAP_BASE_DN = "dc=example,dc=org"
LDAP_ADMIN_DN = "cn=admin,dc=example,dc=org"
LDAP_ADMIN_PASSWORD = "admin_password"
LDAP_DOMAIN = "example.org"


class TestLDAPServer:
    """Управление тестовым LDAP-сервером через Podman CLI."""

    def __init__(self):
        self.cli = CLIControl()

    def start(self):
        """Запускает контейнер с OpenLDAP и загружает тестовые данные."""
        # Удаляем старый контейнер, если остался
        self.cli.execute(
            f"podman rm -f {LDAP_CONTAINER_NAME}",
            is_text=True,
            shell=True
        )

        result = self.cli.execute(
            f"podman run -d "
            f"--name {LDAP_CONTAINER_NAME} "
            f"-e LDAP_ORGANISATION=Test "
            f"-e LDAP_DOMAIN={LDAP_DOMAIN} "
            f"-e LDAP_ADMIN_PASSWORD={LDAP_ADMIN_PASSWORD} "
            f"-p {LDAP_PORT}:{LDAP_PORT} "
            f"osixia/openldap:latest",
            is_text=True,
            shell=True
        )

        print(f"Container started: {result}")

        # Ждём запуска LDAP-сервера
        self._wait_until_ready()

        # Загружаем тестовых пользователей
        self._load_test_data()

    def stop(self):
        """Останавливает и удаляет контейнер."""
        self.cli.execute(
            f"podman rm -f {LDAP_CONTAINER_NAME}",
            user="root",
            password="root",
            is_text=True,
            shell=True
        )

    def _wait_until_ready(self, timeout=30):
        """Ожидает готовности LDAP-сервера."""
        start_time = time.time()
        server = Server("localhost", port=LDAP_PORT, get_info=ALL)

        while time.time() - start_time < timeout:
            try:
                conn = Connection(
                    server,
                    user=LDAP_ADMIN_DN,
                    password=LDAP_ADMIN_PASSWORD,
                    auto_bind=True,
                )
                conn.unbind()
                print("LDAP server is ready!")
                return True
            except Exception as e:
                print(f"Waiting for LDAP server... {e}")
                time.sleep(1)

        raise TimeoutError(f"LDAP server did not start within {timeout} seconds")

    def _load_test_data(self):
        """Загружает тестовых пользователей в LDAP."""
        server = Server("localhost", port=LDAP_PORT, get_info=ALL)
        conn = Connection(
            server,
            user=LDAP_ADMIN_DN,
            password=LDAP_ADMIN_PASSWORD,
            auto_bind=True,
        )

        # Создаём организационную единицу для пользователей
        try:
            conn.add(
                f"ou=users,{LDAP_BASE_DN}",
                ["organizationalUnit", "top"],
                {"ou": "users"},
            )
        except Exception:
            pass  # OU может уже существовать

        # Тестовый пользователь 1
        conn.add(
            f"uid=ldap_user,ou=users,{LDAP_BASE_DN}",
            ["inetOrgPerson", "top"],
            {
                "uid": "ldap_user",
                "cn": "LDAP Test User",
                "sn": "User",
                "givenName": "LDAP",
                "mail": "ldap_user@example.org",
                "userPassword": "correct_password",
            },
        )

        # Тестовый пользователь 2
        conn.add(
            f"uid=new_ldap_user,ou=users,{LDAP_BASE_DN}",
            ["inetOrgPerson", "top"],
            {
                "uid": "new_ldap_user",
                "cn": "New LDAP User",
                "sn": "User",
                "givenName": "New",
                "mail": "new_ldap_user@example.org",
                "userPassword": "password123",
            },
        )

        conn.unbind()
        print("Test users loaded successfully")

    def authenticate(self, username: str, password: str) -> bool:
        """Проверяет учётные данные LDAP-пользователя."""
        server = Server("localhost", port=LDAP_PORT, get_info=ALL)
        user_dn = f"uid={username},ou=users,{LDAP_BASE_DN}"

        try:
            conn = Connection(
                server,
                user=user_dn,
                password=password,
                auto_bind=True,
            )
            conn.unbind()
            return True
        except Exception:
            return False

    def get_user_info(self, username: str) -> dict | None:
        """Получает информацию о пользователе из LDAP."""
        server = Server("localhost", port=LDAP_PORT, get_info=ALL)
        conn = Connection(
            server,
            user=LDAP_ADMIN_DN,
            password=LDAP_ADMIN_PASSWORD,
            auto_bind=True,
        )

        conn.search(
            search_base=f"ou=users,{LDAP_BASE_DN}",
            search_filter=f"(uid={username})",
            attributes=["uid", "cn", "sn", "givenName", "mail"],
        )

        if conn.entries:
            entry = conn.entries[0]
            conn.unbind()
            return {
                "username": str(entry.uid),
                "full_name": str(entry.cn),
                "email": str(entry.mail),
                "first_name": str(entry.givenName),
                "last_name": str(entry.sn),
            }

        conn.unbind()
        return None


@pytest.fixture(scope="session")
def ldap_test_server():
    """Запускает тестовый LDAP-сервер через Podman CLI."""
    server = TestLDAPServer()

    try:
        server.start()
        yield server
    finally:
        server.stop()


# Остальные фикстуры остаются без изменений...
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
