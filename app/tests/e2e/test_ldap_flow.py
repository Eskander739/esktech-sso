"""E2E тесты для LDAP аутентификации."""
import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ldap_login_success(client: AsyncClient, test_user, ldap_test_server):
    """Успешный вход через LDAP."""
    response = await client.post("/oidc/login", data={
        "username": "testuser",
        "password": "testpass123"
    }, follow_redirects=False)
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert "session" in response.cookies


@pytest.mark.asyncio
async def test_ldap_login_invalid_credentials(client: AsyncClient, ldap_test_server):
    """Неверные учётные данные LDAP."""
    response = await client.post("/oidc/login", data={
        "username": "ldap_user",
        "password": "wrong_password"
    })
    assert response.status_code == status.HTTP_200_OK
    assert "Неверный логин или пароль" in response.text


@pytest.mark.asyncio
async def test_ldap_login_missing_fields(client: AsyncClient):
    """Пустые поля логина."""
    response = await client.post("/oidc/login", data={})
    assert "Введите логин и пароль" in response.text


@pytest.mark.asyncio
async def test_ldap_user_data_sync(client: AsyncClient, test_user, ldap_test_server):
    """После LDAP входа пользователь создаётся в локальной БД."""
    await client.post("/oidc/login", data={
        "username": "testuser",
        "password": "testpass123"
    })
    resp = await client.get("/admin/users/list")
    users = resp.json()
    assert any(u["username"] == "testuser" for u in users)