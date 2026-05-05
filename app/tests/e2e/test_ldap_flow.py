"""E2E тесты для LDAP аутентификации."""
import pytest
from constants import ApiVersion
from fastapi import status
from httpx import AsyncClient
from models.msg import Message
from services.localization import _


@pytest.mark.asyncio

async def test_ldap_login_success(client: AsyncClient, test_user, ldap_test_server):
    """Успешный вход через LDAP."""
    response = await client.post("/login", data={
        "username": "ldap_user",
        "password": "correct_password"
    }, follow_redirects=False)
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert "session" in response.cookies


@pytest.mark.asyncio
async def test_ldap_login_invalid_credentials(client: AsyncClient, test_user, ldap_test_server):
    """Неверные учётные данные LDAP."""
    response = await client.post("/login", data={
        "username": "test@example.com",
        "password": "wrong_password"
    })
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert _(Message.invalid_password_or_login) in response.text


@pytest.mark.asyncio
async def test_ldap_login_missing_fields(client: AsyncClient):
    """Пустые поля логина."""
    response = await client.post("/login", data={})
    assert _(Message.input_login_and_password) in response.text


@pytest.mark.asyncio
async def test_ldap_user_data_sync(client: AsyncClient, test_user, ldap_test_server):
    """После LDAP входа пользователь создаётся в локальной БД."""
    await client.post("/login", data={
        "username": "test@example.com",
        "password": "testpass123"
    })
    resp = await client.get(f"{ApiVersion.V0}/admin/users/list")
    users = resp.json()
    assert any(u["username"] == "testuser" for u in users)
