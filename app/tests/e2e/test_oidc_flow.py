"""E2E тесты для OIDC потока."""
import random
from typing import Any

import pytest
from constants import ApiVersion
from fastapi import status
from httpx import AsyncClient
from tests.config_tests_sample import ConfigTestsSample
from utils.password_validator import hash_password


def get_app(client: AsyncClient) -> Any:
    """Получить экземпляр FastAPI приложения из тестового клиента."""
    transport = client._transport
    return transport.app  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_oidc_authorization_code_flow(client: AsyncClient):
    """Полный OIDC Authorization Code Flow (внутренний OIDC-сервер)."""
    app = get_app(client)

    user_db = app.state.user_db
    hashed = hash_password("testpass123")
    await user_db.create(
        username="testuser",
        email="test@example.com",
        hashed_password=hashed,
        full_name="Test User",
        is_active=True,
    )

    create_resp = await client.post(f"{ApiVersion.V0}/admin/clients", json={
        "name": "Test App",
        "redirect_uris": "http://localhost:8000/callback",
    })
    assert create_resp.status_code == status.HTTP_200_OK
    client_data = create_resp.json()
    client_id = client_data["client_id"]
    client_secret = client_data["client_secret"]

    auth_resp = await client.get(
        f"{ApiVersion.V0}/oidc/authorize",
        params={
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": "http://localhost:8000/callback",
            "scope": "openid profile email",
        },
        follow_redirects=False,
    )
    assert auth_resp.status_code in [status.HTTP_302_FOUND, status.HTTP_307_TEMPORARY_REDIRECT]
    assert "/oidc/login" in auth_resp.headers["location"]

    login_resp = await client.post(f"{ApiVersion.V0}/oidc/login", data={
        "username": "testuser",
        "password": "testpass123",
    }, follow_redirects=False)
    assert login_resp.status_code == status.HTTP_307_TEMPORARY_REDIRECT

    auth2_resp = await client.get(
        f"{ApiVersion.V0}/oidc/authorize",
        params={
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": "http://localhost:8000/callback",
            "scope": "openid profile email",
        },
        follow_redirects=False,
    )
    assert auth2_resp.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    location = auth2_resp.headers["location"]
    assert "code=" in location

    code = location.split("code=")[1].split("&")[0]
    token_resp = await client.post(f"{ApiVersion.V0}/oidc/token", data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "http://localhost:8000/callback",
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert token_resp.status_code == status.HTTP_200_OK
    token_data = token_resp.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert "id_token" in token_data


@pytest.mark.asyncio
async def test_oidc_client_credentials_flow(client: AsyncClient):
    """OAuth2 Client Credentials Grant (внутренний OIDC-сервер)."""
    create_resp = await client.post(f"{ApiVersion.V0}/admin/clients", json={
        "name": "Service App",
        "redirect_uris": "http://localhost:8000/callback",
    })
    assert create_resp.status_code == status.HTTP_200_OK
    client_data = create_resp.json()

    token_resp = await client.post(f"{ApiVersion.V0}/oidc/token", data={
        "grant_type": "client_credentials",
        "client_id": client_data["client_id"],
        "client_secret": client_data["client_secret"],
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert token_resp.status_code == status.HTTP_200_OK
    assert "access_token" in token_resp.json()


@pytest.mark.asyncio
async def test_oidc_refresh_token_flow(client: AsyncClient):
    """Обновление токена через refresh_token (внутренний OIDC-сервер)."""
    app = get_app(client)

    user_db = app.state.user_db
    hashed = hash_password("testpass123")
    username = f"testuser2-{random.randint(100000, 999999)}"
    email = f"test2-{random.randint(100000, 999999)}@example.com"
    await user_db.create(
        username=username,
        email=email,
        hashed_password=hashed,
        full_name="Test User 2",
        is_active=True,
    )

    create_resp = await client.post(f"{ApiVersion.V0}/admin/clients", json={
        "name": "Refresh Test App",
        "redirect_uris": "http://localhost:8000/callback",
    })
    assert create_resp.status_code == status.HTTP_200_OK
    client_data = create_resp.json()
    client_id = client_data["client_id"]
    client_secret = client_data["client_secret"]

    auth_resp = await client.get(
        f"{ApiVersion.V0}/oidc/authorize",
        params={
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": "http://localhost:8000/callback",
            "scope": "openid",
        },
        follow_redirects=False,
    )
    assert auth_resp.status_code in [status.HTTP_302_FOUND, status.HTTP_307_TEMPORARY_REDIRECT]

    login_resp = await client.post(f"{ApiVersion.V0}/oidc/login", data={
        "username": username,
        "password": "testpass123",
    }, follow_redirects=False)
    assert login_resp.status_code == status.HTTP_307_TEMPORARY_REDIRECT

    auth2_resp = await client.get(
        f"{ApiVersion.V0}/oidc/authorize",
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

    token_resp = await client.post(f"{ApiVersion.V0}/oidc/token", data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "http://localhost:8000/callback",
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert token_resp.status_code == status.HTTP_200_OK
    token_data = token_resp.json()
    refresh_token = token_data["refresh_token"]

    resp = await client.post(f"{ApiVersion.V0}/oidc/token", data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert resp.status_code == status.HTTP_200_OK
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_oidc_userinfo_endpoint(client: AsyncClient, auth_token):
    """Получение userinfo по access_token (внутренний OIDC-сервер)."""
    resp = await client.get(
        f"{ApiVersion.V0}/oidc/userinfo",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert "sub" in resp.json()
    assert "email" in resp.json()


# ----------------- Тесты с внешним GitLab OIDC ------------------------------
@pytest.mark.asyncio
async def test_gitlab_oidc_discovery(gitlab_oidc_server):
    """Проверяет, что GitLab отдаёт корректный OpenID Connect Discovery документ."""
    async with AsyncClient() as client:
        resp = await client.get(gitlab_oidc_server.well_known_url)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["issuer"] == gitlab_oidc_server.issuer
    assert "authorization_endpoint" in data
    assert "token_endpoint" in data
    assert "userinfo_endpoint" in data
    assert "response_types_supported" in data


@pytest.mark.asyncio
async def test_gitlab_oidc_authorization_redirect(gitlab_oidc_server):
    """Проверяет, что GitLab перенаправляет на страницу логина при запросе авторизации."""
    authorization_url = f"http://{ConfigTestsSample.GITLAB_HOST}:{ConfigTestsSample.GITLAB_HTTP_PORT}/oauth/authorize"
    async with AsyncClient() as client:
        resp = await client.get(
            authorization_url,
            params={
                "client_id": gitlab_oidc_server.client_id,
                "response_type": "code",
                "redirect_uri": ConfigTestsSample.GITLAB_REDIRECT_URI,
                "scope": "openid",
            },
            follow_redirects=False,
        )

    assert resp.status_code == status.HTTP_302_FOUND
    assert "/users/sign_in" in resp.headers.get("location", "")
