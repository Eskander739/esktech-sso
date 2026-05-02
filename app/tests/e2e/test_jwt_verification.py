"""E2E тесты для JWT верификации."""
import jwt
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_jwt_validation_required_endpoint(client: AsyncClient, auth_token):
    """Доступ к защищённому эндпоинту с валидным токеном."""
    resp = await client.get(
        "/oidc/userinfo",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.skip
async def test_jwt_missing_token(client: AsyncClient):
    """Запрос без токена."""
    resp = await client.get("/oidc/userinfo")
    assert resp.status_code == 401
    assert "Bearer" in resp.headers.get("WWW-Authenticate", "")


@pytest.mark.asyncio
async def test_jwt_invalid_token(client: AsyncClient):
    """Неверный токен."""
    resp = await client.get(
        "/oidc/userinfo",
        headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
@pytest.mark.skip
async def test_jwt_expired_token(client: AsyncClient, expired_token):
    """Просроченный токен."""
    resp = await client.get(
        "/oidc/userinfo",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert resp.status_code == 401
    assert "expired" in resp.text.lower()


@pytest.mark.asyncio
async def test_jwt_wrong_audience(client: AsyncClient):
    """Токен с неверной аудиторией."""
    wrong_aud_token = jwt.encode(
        {"sub": "user", "aud": "wrong_service"},
        "secret_key",
        algorithm="HS256"
    )
    resp = await client.get(
        "/oidc/userinfo",
        headers={"Authorization": f"Bearer {wrong_aud_token}"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_jwt_missing_sub_claim(client: AsyncClient):
    """Токен без sub."""
    token = jwt.encode({"aud": "sso"}, "secret_key", algorithm="HS256")
    resp = await client.get(
        "/oidc/userinfo",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
@pytest.mark.skip
async def test_jwk_endpoint_returns_keys(client: AsyncClient):
    """Эндпоинт JWKS отдаёт публичные ключи."""
    resp = await client.get("/oidc/jwks")
    assert resp.status_code == 200
    data = resp.json()
    assert "keys" in data
    assert len(data["keys"]) > 0
    assert data["keys"][0]["kty"] == "RSA"