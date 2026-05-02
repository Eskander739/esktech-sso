"""E2E тесты для OIDC потока."""
from typing import Any

import pytest
from auth.password_validator import hash_password
from fastapi import status
from httpx import AsyncClient


def get_app(client: AsyncClient) -> Any:
    """Получить экземпляр FastAPI приложения из тестового клиента."""
    transport = client._transport
    # Приведение к Any, чтобы mypy не ругался на отсутствие атрибута app
    return transport.app  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_oidc_authorization_code_flow(client: AsyncClient):
    """Полный OIDC Authorization Code Flow."""
    app = get_app(client)

    # Создаём тестового пользователя в БД
    user_db = app.state.user_db
    hashed = hash_password("testpass123")
    await user_db.create(
        username="testuser",
        email="test@example.com",
        hashed_password=hashed,
        full_name="Test User",
        is_active=True
    )

    # 1. Создаём OIDC клиента
    create_resp = await client.post("/admin/clients", json={
        "name": "Test App",
        "redirect_uris": "http://localhost:8000/callback"
    })
    assert create_resp.status_code == status.HTTP_200_OK
    client_data = create_resp.json()
    client_id = client_data["client_id"]
    client_secret = client_data["client_secret"]

    # 2. Запрос авторизации (редирект на логин)
    auth_resp = await client.get(
        "/oidc/authorize",
        params={
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": "http://localhost:8000/callback",
            "scope": "openid profile email"
        },
        follow_redirects=False
    )
    assert auth_resp.status_code in [302, 307]
    assert "/oidc/login" in auth_resp.headers["location"]

    # 3. Логинимся
    login_resp = await client.post("/oidc/login", data={
        "username": "testuser",
        "password": "testpass123"
    }, follow_redirects=False)
    assert login_resp.status_code == status.HTTP_307_TEMPORARY_REDIRECT

    # 4. Повторный запрос авторизации (уже с сессией)
    auth2_resp = await client.get(
        "/oidc/authorize",
        params={
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": "http://localhost:8000/callback",
            "scope": "openid profile email"
        },
        follow_redirects=False
    )
    assert auth2_resp.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    location = auth2_resp.headers["location"]
    assert "code=" in location

    # 5. Обмен кода на токены
    code = location.split("code=")[1].split("&")[0]
    token_resp = await client.post("/oidc/token", data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "http://localhost:8000/callback"
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert token_resp.status_code == status.HTTP_200_OK
    token_data = token_resp.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert "id_token" in token_data

    # Сохраняем refresh_token для следующего теста
    return token_data["refresh_token"]


@pytest.mark.asyncio
async def test_oidc_client_credentials_flow(client: AsyncClient):
    """OAuth2 Client Credentials Grant."""
    create_resp = await client.post("/admin/clients", json={
        "name": "Service App",
        "redirect_uris": "http://localhost:8000/callback"
    })
    assert create_resp.status_code == status.HTTP_200_OK
    client_data = create_resp.json()

    token_resp = await client.post("/oidc/token", data={
        "grant_type": "client_credentials",
        "client_id": client_data["client_id"],
        "client_secret": client_data["client_secret"]
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert token_resp.status_code == status.HTTP_200_OK
    assert "access_token" in token_resp.json()


@pytest.mark.asyncio
async def test_oidc_refresh_token_flow(client: AsyncClient):
    """Обновление токена через refresh_token."""
    app = get_app(client)

    # Сначала создаём пользователя и клиента, получаем реальный refresh_token
    user_db = app.state.user_db
    hashed = hash_password("testpass123")
    await user_db.create(
        username="testuser2",
        email="test2@example.com",
        hashed_password=hashed,
        full_name="Test User 2",
        is_active=True
    )

    # Создаём клиента
    create_resp = await client.post("/admin/clients", json={
        "name": "Refresh Test App",
        "redirect_uris": "http://localhost:8000/callback"
    })
    assert create_resp.status_code == status.HTTP_200_OK
    client_data = create_resp.json()
    client_id = client_data["client_id"]
    client_secret = client_data["client_secret"]

    # Первый запрос авторизации (перенаправляет на логин)
    auth_resp = await client.get(
        "/oidc/authorize",
        params={
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": "http://localhost:8000/callback",
            "scope": "openid"
        },
        follow_redirects=False
    )
    # Проверяем, что нас перенаправляют на страницу входа
    assert auth_resp.status_code in [302, 307]

    # Логинимся
    login_resp = await client.post("/oidc/login", data={
        "username": "testuser2",
        "password": "testpass123"
    }, follow_redirects=False)
    assert login_resp.status_code == status.HTTP_307_TEMPORARY_REDIRECT

    # Получаем код
    auth2_resp = await client.get(
        "/oidc/authorize",
        params={
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": "http://localhost:8000/callback",
            "scope": "openid"
        },
        follow_redirects=False
    )
    location = auth2_resp.headers["location"]
    code = location.split("code=")[1].split("&")[0]

    # Обмениваем код на токены
    token_resp = await client.post("/oidc/token", data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "http://localhost:8000/callback"
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert token_resp.status_code == status.HTTP_200_OK
    token_data = token_resp.json()
    refresh_token = token_data["refresh_token"]

    # Теперь обновляем токен
    resp = await client.post("/oidc/token", data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert resp.status_code == status.HTTP_200_OK
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_oidc_userinfo_endpoint(client: AsyncClient, auth_token):
    """Получение userinfo по access_token."""
    resp = await client.get(
        "/oidc/userinfo",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert "sub" in resp.json()
    assert "email" in resp.json()