"""E2E тесты для LDAP аутентификации."""
import pytest
from httpx import AsyncClient


@pytest.mark.e2e
@pytest.mark.skip(reason="LDAP аутентификация не настроена в текущей версии")
@pytest.mark.asyncio
async def test_ldap_login_success(client: AsyncClient, ldap_test_server):
    """Успешный вход через LDAP."""
    response = await client.post("/oidc/login", data={
        "username": "ldap_user",
        "password": "correct_password"
    }, follow_redirects=False)
    assert response.status_code == 302
    assert "session" in response.cookies


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_ldap_login_invalid_credentials(client: AsyncClient):
    """Неверные учётные данные LDAP."""
    response = await client.post("/oidc/login", data={
        "username": "ldap_user",
        "password": "wrong_password"
    })
    assert response.status_code == 200
    assert "Неверный логин или пароль" in response.text


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_ldap_login_missing_fields(client: AsyncClient):
    """Пустые поля логина."""
    response = await client.post("/oidc/login", data={})
    assert "Введите логин и пароль" in response.text


@pytest.mark.e2e
@pytest.mark.skip(reason="LDAP аутентификация не настроена в текущей версии")
@pytest.mark.asyncio
async def test_ldap_user_data_sync(client: AsyncClient, ldap_test_server):
    """После LDAP входа пользователь создаётся в локальной БД."""
    await client.post("/oidc/login", data={
        "username": "new_ldap_user",
        "password": "password123"
    })
    resp = await client.get("/admin/users/list")
    users = resp.json()
    assert any(u["username"] == "new_ldap_user" for u in users)