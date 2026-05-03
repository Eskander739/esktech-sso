"""E2E тесты для отзыва токенов."""
import base64

import pytest
from fastapi import status
from httpx import AsyncClient
from utils.password_validator import hash_password


@pytest.mark.asyncio
async def test_revoke_refresh_token_endpoint(client: AsyncClient, setup_test_db):
    """Тест отзыва refresh токена через API."""
    user_db = client._transport.app.state.user_db  # type: ignore[attr-defined]
    hashed = hash_password("testpass123")
    await user_db.create(
        username="revoke_refresh_user",
        email="refresh_revoke@test.com",
        hashed_password=hashed,
        full_name="Refresh Revoke User",
        is_active=True,
    )

    create_resp = await client.post("/admin/clients", json={
        "name": "Refresh Revoke App",
        "redirect_uris": "http://localhost:8000/callback",
    })
    client_data = create_resp.json()
    client_id = client_data["client_id"]
    client_secret = client_data["client_secret"]

    # Получаем код
    await client.get("/oidc/authorize", params={
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": "http://localhost:8000/callback",
        "scope": "openid",
    }, follow_redirects=False)
    await client.post("/oidc/login", data={
        "username": "revoke_refresh_user",
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

    # Отзываем refresh токен
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    revoke_resp = await client.post(
        "/oidc/revoke",
        data={"token": refresh_token, "token_type_hint": "refresh_token"},
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )
    assert revoke_resp.status_code == status.HTTP_200_OK

    # Пытаемся обновить токен через отозванный refresh
    refresh_resp = await client.post("/oidc/token", data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    })
    assert refresh_resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_revoke_without_auth(client: AsyncClient):
    """Отзыв токена без авторизации клиента."""
    revoke_resp = await client.post(
        "/oidc/revoke",
        data={"token": "some_token"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert revoke_resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_revoke_without_token(client: AsyncClient, setup_test_db):
    """Отзыв без указания токена."""
    create_resp = await client.post("/admin/clients", json={
        "name": "No Token App",
        "redirect_uris": "http://localhost:8000/callback",
    })
    client_data = create_resp.json()

    credentials = base64.b64encode(
        f"{client_data['client_id']}:{client_data['client_secret']}".encode()
    ).decode()

    revoke_resp = await client.post(
        "/oidc/revoke",
        data={},
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )
    assert revoke_resp.status_code == status.HTTP_401_UNAUTHORIZED
