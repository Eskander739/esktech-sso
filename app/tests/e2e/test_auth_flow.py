"""E2E тесты для auth flow."""
import pytest
from constants import ApiVersion
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_authorize_redirect(client: AsyncClient, test_client_app):
    """Тест редиректа на страницу логина."""
    response = await client.get(
        f"{ApiVersion.V0}/oidc/authorize",
        params={
            "client_id": test_client_app["client_id"],
            "redirect_uri": "http://localhost:8000/callback",
            "response_type": "code",
            "scope": "openid"
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT or response.status_code == status.HTTP_302_FOUND
    assert "/oidc/login" in response.headers["location"]
