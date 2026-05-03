"""E2E тесты для OPAQUE токенов (реальный HTTP)."""
import pytest
from config import settings
from constants import AccessTokenFormat
from fastapi import status
from httpx import AsyncClient
from utils.password_validator import hash_password


@pytest.mark.asyncio
async def test_authorization_code_flow_opaque(client: AsyncClient, setup_test_db):
    """Полный OIDC-поток с получением opaque access_token."""
    # Устанавливаем формат токена в opaque для теста
    original_format = settings.ACCESS_TOKEN_FORMAT
    settings.ACCESS_TOKEN_FORMAT = AccessTokenFormat.OPAQUE

    # Создаём тестового пользователя
    user_db = client._transport.app.state.user_db  # type: ignore[attr-defined]
    hashed = hash_password("testpass123")
    await user_db.create(
        username="opaque_user",
        email="opaque@test.com",
        hashed_password=hashed,
        full_name="Opaque User",
        is_active=True,
    )

    # Создаём OIDC клиента
    create_resp = await client.post("/admin/clients", json={
        "name": "Opaque Test App",
        "redirect_uris": "http://localhost:8000/callback",
    })
    assert create_resp.status_code == status.HTTP_200_OK
    client_data = create_resp.json()
    client_id = client_data["client_id"]
    client_secret = client_data["client_secret"]

    # Авторизация
    auth_resp = await client.get(
        "/oidc/authorize",
        params={
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": "http://localhost:8000/callback",
            "scope": "openid",
        },
        follow_redirects=False,
    )
    assert auth_resp.status_code in [302, 307]

    # Логин
    login_resp = await client.post("/oidc/login", data={
        "username": "opaque_user",
        "password": "testpass123",
    }, follow_redirects=False)
    assert login_resp.status_code in [302, 307]

    # Повторный запрос кода
    auth2_resp = await client.get(
        "/oidc/authorize",
        params={
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": "http://localhost:8000/callback",
            "scope": "openid",
        },
        follow_redirects=False,
    )
    location = auth2_resp.headers["location"]
    code = location.split("code=")[1].split("&")[0]

    # Обмен на токены
    token_resp = await client.post("/oidc/token", data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "http://localhost:8000/callback",
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert token_resp.status_code == status.HTTP_200_OK
    token_data = token_resp.json()
    access_token = token_data["access_token"]

    # Проверяем, что access_token не является JWT (не содержит точек)
    assert access_token.count('.') == 0

    # Проверяем userinfo с opaque токеном
    userinfo_resp = await client.get(
        "/oidc/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert userinfo_resp.status_code == status.HTTP_200_OK
    userinfo = userinfo_resp.json()
    assert userinfo["preferred_username"] == "opaque_user"

    # Возвращаем оригинальный формат
    settings.ACCESS_TOKEN_FORMAT = original_format


@pytest.mark.asyncio
async def test_refresh_token_opaque(client: AsyncClient, setup_test_db):
    """Обновление opaque токена через refresh_token."""
    original_format = settings.ACCESS_TOKEN_FORMAT
    settings.ACCESS_TOKEN_FORMAT = AccessTokenFormat.OPAQUE

    # Создаём пользователя и клиента (аналогично предыдущему)
    user_db = client._transport.app.state.user_db  # type: ignore[attr-defined]
    hashed = hash_password("testpass123")
    await user_db.create(
        username="opaque_refresh",
        email="refresh@test.com",
        hashed_password=hashed,
        full_name="Refresh User",
        is_active=True,
    )

    create_resp = await client.post("/admin/clients", json={
        "name": "Refresh Opaque",
        "redirect_uris": "http://localhost:8000/callback",
    })
    client_data = create_resp.json()
    client_id = client_data["client_id"]
    client_secret = client_data["client_secret"]

    # Получаем код (сначала логин)
    await client.get("/oidc/authorize", params={
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": "http://localhost:8000/callback",
        "scope": "openid",
    }, follow_redirects=False)
    await client.post("/oidc/login", data={
        "username": "opaque_refresh",
        "password": "testpass123",
    }, follow_redirects=False)
    auth_resp = await client.get("/oidc/authorize", params={
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": "http://localhost:8000/callback",
        "scope": "openid",
    }, follow_redirects=False)
    code = auth_resp.headers["location"].split("code=")[1].split("&")[0]

    token_resp = await client.post("/oidc/token", data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "http://localhost:8000/callback",
    })
    refresh_token = token_resp.json()["refresh_token"]

    # Обновляем
    refresh_resp = await client.post("/oidc/token", data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    })
    assert refresh_resp.status_code == status.HTTP_200_OK
    new_token = refresh_resp.json()["access_token"]
    assert new_token.count('.') == 0

    settings.ACCESS_TOKEN_FORMAT = original_format