"""Фикстуры для тестов."""
import time
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from auth_server import create_authorization_server
from config import settings
from db.oauth import OAuthClientDB, OAuthCodeDB, OAuthTokenDB
from db.users import UserDB
from httpx import ASGITransport, AsyncClient
from ldap3 import ALL, Connection, Server
from ldap3.core.exceptions import LDAPException
from log import logger
from main import app
from services.pool.db_pool import DBPool
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from tests.config_tests_sample import ConfigTestsSample
from utils.cli import CLIControl
from utils.password_validator import hash_password

settings.DATABASE_URL = "postgresql+asyncpg://sso_user:sso_pass@localhost:5432/sso"


class TestLDAPServer:
    """Управление тестовым LDAP-сервером через Podman CLI."""

    def __init__(self):
        self.cli = CLIControl()

    def start(self):
        """Запускает контейнер с OpenLDAP и загружает тестовые данные."""
        self.cli.execute(
            f"podman rm -f {ConfigTestsSample.LDAP_CONTAINER_NAME}",
            is_text=True,
            shell=True,
        )

        result = self.cli.execute(
            f"podman run -d "
            f"--name {ConfigTestsSample.LDAP_CONTAINER_NAME} "
            f"-e LDAP_ORGANISATION=Test "
            f"-e LDAP_DOMAIN={ConfigTestsSample.LDAP_DOMAIN} "
            f"-e LDAP_ADMIN_PASSWORD={ConfigTestsSample.LDAP_ADMIN_PASSWORD} "
            f"-p {ConfigTestsSample.LDAP_PORT}:{ConfigTestsSample.LDAP_PORT} "
            f"osixia/openldap:latest",
            is_text=True,
            shell=True,
        )

        print(f"Container started: {result}")

        self._wait_until_ready()
        self._load_test_data()

    def stop(self):
        """Останавливает и удаляет контейнер."""
        self.cli.execute(
            f"podman rm -f {ConfigTestsSample.LDAP_CONTAINER_NAME}",
            is_text=True,
            shell=True,
        )

    def _wait_until_ready(self, timeout=30):
        """Ожидает готовности LDAP-сервера."""
        start_time = time.time()
        server = Server("localhost", port=ConfigTestsSample.LDAP_PORT, get_info=ALL)

        while time.time() - start_time < timeout:
            try:
                conn = Connection(
                    server,
                    user=ConfigTestsSample.LDAP_ADMIN_DN,
                    password=ConfigTestsSample.LDAP_ADMIN_PASSWORD,
                    auto_bind=True,
                )
                conn.unbind()
                print("LDAP server is ready!")
                return True
            except LDAPException as e:
                print(f"Waiting for LDAP server... {e}")
                time.sleep(1)

        raise TimeoutError(f"LDAP server did not start within {timeout} seconds")

    def _load_test_data(self):
        """Загружает тестовых пользователей в LDAP."""
        server = Server("localhost", port=ConfigTestsSample.LDAP_PORT, get_info=ALL)
        conn = Connection(
            server,
            user=ConfigTestsSample.LDAP_ADMIN_DN,
            password=ConfigTestsSample.LDAP_ADMIN_PASSWORD,
            auto_bind=True,
        )

        try:
            conn.add(
                f"ou=users,{ConfigTestsSample.LDAP_BASE_DN}",
                ["organizationalUnit", "top"],
                {"ou": "users"},
            )
        except LDAPException:
            pass  # OU может уже существовать

        # Тестовый пользователь 1
        conn.add(
            f"uid=ldap_user,ou=users,{ConfigTestsSample.LDAP_BASE_DN}",
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
            f"uid=new_ldap_user,ou=users,{ConfigTestsSample.LDAP_BASE_DN}",
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
        server = Server("localhost", port=ConfigTestsSample.LDAP_PORT, get_info=ALL)
        user_dn = f"uid={username},ou=users,{ConfigTestsSample.LDAP_BASE_DN}"

        try:
            conn = Connection(
                server,
                user=user_dn,
                password=password,
                auto_bind=True,
            )
            conn.unbind()
            return True
        except LDAPException:
            return False

    def get_user_info(self, username: str) -> dict | None:
        """Получает информацию о пользователе из LDAP."""
        server = Server("localhost", port=ConfigTestsSample.LDAP_PORT, get_info=ALL)
        conn = Connection(
            server,
            user=ConfigTestsSample.LDAP_ADMIN_DN,
            password=ConfigTestsSample.LDAP_ADMIN_PASSWORD,
            auto_bind=True,
        )

        conn.search(
            search_base=f"ou=users,{ConfigTestsSample.LDAP_BASE_DN}",
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


class TestGitLabServer:
    """Управление тестовым GitLab-сервером (как OIDC-провайдером) через Podman CLI."""

    def __init__(self):
        self.cli = CLIControl()
        self.client_id = None
        self.client_secret = None
        self.issuer = f"http://{ConfigTestsSample.GITLAB_HOST}:{ConfigTestsSample.GITLAB_HTTP_PORT}"
        self.well_known_url = f"{self.issuer}/.well-known/openid-configuration"

    def start(self):
        """Запускает GitLab CE в Podman и настраивает OAuth-приложение."""
        # Удаляем старый контейнер, если остался
        self.cli.execute(
            f"podman rm -f {ConfigTestsSample.GITLAB_CONTAINER_NAME}",
            is_text=True,
            shell=True,
        )

        self.cli.execute(
            f"podman run -d "
            f"--name {ConfigTestsSample.GITLAB_CONTAINER_NAME} "
            f"--hostname {ConfigTestsSample.GITLAB_HOST} "
            f"-e GITLAB_OMNIBUS_CONFIG='"
            f"external_url \"http://{ConfigTestsSample.GITLAB_HOST}:{ConfigTestsSample.GITLAB_HTTP_PORT}\"; "
            f"gitlab_rails[\"initial_root_password\"] = \"{ConfigTestsSample.GITLAB_ROOT_PASSWORD}\"; "
            f"gitlab_rails[\"resource_owner_password_credentials_enabled\"] = true; "
            f"gitlab_rails[\"gitlab_signup_enabled\"] = false; "
            f"gitlab_rails[\"gitlab_signin_enabled\"] = true; "
            f"' "
            f"-p {ConfigTestsSample.GITLAB_HTTP_PORT}:{ConfigTestsSample.GITLAB_HTTP_PORT} "
            f"gitlab/gitlab-ce:latest",
            is_text=True,
            shell=True,
            timeout=ConfigTestsSample.GITLAB_CONTAINER_TIMEOUT, # 10 минут на первый запуск, если образ не был до этого скачан
        )

        print("GitLab container starting (this may take a few minutes)...")
        self._wait_until_ready()
        print("GitLab is ready!")
        self._configure_oauth_app()

    def stop(self):
        """Останавливает и удаляет контейнер."""
        self.cli.execute(
            f"podman rm -f {ConfigTestsSample.GITLAB_CONTAINER_NAME}",
            is_text=True,
            shell=True,
            timeout=ConfigTestsSample.GITLAB_CONTAINER_TIMEOUT,  # Остановка и удаление контейнера также может быть долгой
        )

    def _wait_until_ready(self, timeout=ConfigTestsSample.GITLAB_CONTAINER_TIMEOUT):
        """Ожидает, пока GitLab станет доступен (отвечает 302 на /)."""
        start_time = time.time()
        url = f"http://{ConfigTestsSample.GITLAB_HOST}:{ConfigTestsSample.GITLAB_HTTP_PORT}/"
        while time.time() - start_time < timeout:
            try:
                response = httpx.get(url, timeout=5, follow_redirects=False)
                if response.status_code == 302:  # GitLab редиректит на /users/sign_in
                    return True
            except httpx.RequestError:
                pass
            time.sleep(5)
        raise TimeoutError(f"GitLab did not start within {timeout} seconds")

    def _configure_oauth_app(self):
        """Создаёт OAuth-приложение в GitLab от имени root."""
        admin_token = self._get_admin_token()
        if not admin_token:
            raise RuntimeError("Failed to obtain GitLab admin token")

        # Создаём приложение через API
        resp = httpx.post(
            f"http://{ConfigTestsSample.GITLAB_HOST}:{ConfigTestsSample.GITLAB_HTTP_PORT}/api/v4/applications",
            json={
                "name": ConfigTestsSample.GITLAB_OAUTH_APP_NAME,
                "redirect_uri": ConfigTestsSample.GITLAB_REDIRECT_URI,
                "scopes": "openid profile email",
                "confidential": False,  # public client для тестов
            },
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30,
        )
        if resp.status_code != 201:
            raise RuntimeError(f"Failed to create OAuth app: {resp.text}")

        app_data = resp.json()
        self.client_id = app_data["application_id"]
        self.client_secret = app_data["secret"]
        print(f"GitLab OAuth app created: client_id={self.client_id}")

    def _get_admin_token(self):
        """Получает personal access token для root пользователя."""
        # Сначала получаем токен через OAuth или создаём personal access token от root
        # Проще всего создать PAT через API с использованием начального пароля root
        # GitLab 16+ позволяет создать PAT при первом входе, но мы можем использовать
        # Resource Owner Password Credentials Grant (ROPC) с правами администратора,
        # если включено. Включим ROPC через переменную окружения при запуске.
        # Мы не включали, поэтому используем обходной путь: создаём PAT через сессию
        # веб-интерфейса? Это сложно. Вместо этого используем ROPC, предварительно
        # разрешив его в конфигурации контейнера.
        # Дополним конфигурацию GitLab: gitlab_rails['omniauth_enabled'] = false
        # и добавим gitlab_rails['incoming_email_enabled'] = false.
        # Но для простоты можно создать пользователя и токен через rails console,
        # что не автоматизируемо. Поэтому самый надёжный способ:
        # 1. Заранее создать токен через web UI и передать его переменной.
        # Для автоматических тестов лучше использовать предварительно созданный
        # образ с настройками. Однако для демонстрации предложу вариант с
        # Resource Owner Password Credentials flow, который нужно явно включить.
        # Обновим команду запуска: добавим переменную GITLAB_OMNIBUS_CONFIG с
        # включением gitlab_rails['resource_owner_password_credentials_enabled'] = true.
        # Это позволит нам обменять username/password на токен.
        # Изменяем команду запуска в методе start.
        # После изменения, здесь вызываем получение токена через ROPC.
        token_url = f"http://{ConfigTestsSample.GITLAB_HOST}:{ConfigTestsSample.GITLAB_HTTP_PORT}/oauth/token"
        resp = httpx.post(
            token_url,
            data={
                "grant_type": "password",
                "username": "root",
                "password": ConfigTestsSample.GITLAB_ROOT_PASSWORD,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to get admin token: {resp.text}")
        return resp.json()["access_token"]


@pytest.fixture(scope="session")
def ldap_test_server():
    """Запускает тестовый LDAP-сервер через Podman CLI."""
    server = TestLDAPServer()
    try:
        server.start()
        yield server
    finally:
        server.stop()


@pytest.fixture(scope="session")
def gitlab_oidc_server():
    """Запускает тестовый GitLab-сервер как OIDC-провайдер."""
    server = TestGitLabServer()
    try:
        server.start()
        yield server
    finally:
        server.stop()


@pytest.fixture(autouse=True, scope="function")
async def setup_test_db():
    """Настройка тестовой БД для каждого теста с очисткой данных."""
    db_pool = DBPool()
    await db_pool.create_tables()

    async with db_pool.get_connection() as session:
        try:
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
    app.state.logger = logger
    app.state.ldap_uri = "localhost"

    yield

    await db_pool.close_pool()

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
    token = server._create_jwt_access_token(
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