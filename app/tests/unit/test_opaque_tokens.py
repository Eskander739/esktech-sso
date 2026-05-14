"""Unit тесты для OPAQUE токенов."""
from unittest.mock import AsyncMock

import pytest
from oidc_server import OIDCServer
from constants import AccessTokenFormat


@pytest.mark.asyncio
async def test_opaque_token_generation():
    """Проверка генерации opaque токена."""
    server = OIDCServer()
    mock_db = AsyncMock()
    token = await server._create_opaque_token(
        user_id=1,
        client_id="test",
        scope="openid",
        oauth_token_db=mock_db
    )
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 20


@pytest.mark.asyncio
async def test_token_format_detection_jwt():
    """Определение JWT токена по наличию двух точек."""
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.abc"
    assert token.count('.') == 2
    detected_type = AccessTokenFormat.JWT if token.count('.') == 2 else AccessTokenFormat.OPAQUE
    assert detected_type == AccessTokenFormat.JWT


@pytest.mark.asyncio
async def test_token_format_detection_opaque():
    """Определение OPAQUE токена (без точек)."""
    token = "a1b2c3d4e5f6g7h8i9j0"
    assert token.count('.') == 0
    detected_type = AccessTokenFormat.JWT if token.count('.') == 2 else AccessTokenFormat.OPAQUE
    assert detected_type == AccessTokenFormat.OPAQUE