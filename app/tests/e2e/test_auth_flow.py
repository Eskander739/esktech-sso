import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_page(client: AsyncClient):
    response = await client.get("/oidc/login")
    assert response.status_code == 200
    assert "Вход в систему" in response.text


@pytest.mark.asyncio
async def test_authorize_redirect(client: AsyncClient):
    response = await client.get("/oidc/authorize", follow_redirects=False)
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
