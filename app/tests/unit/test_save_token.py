from unittest.mock import AsyncMock, MagicMock

import pytest
from auth_server import create_authorization_server
from authlib.oauth2.rfc6749.requests import OAuth2Request


@pytest.mark.asyncio
async def test_save_token():
    """Проверка сохранения токена."""
    server = await create_authorization_server()

    server.save_token = MagicMock()

    token_data = {
        "access_token": "test_access_123",
        "refresh_token": "test_refresh_456",
        "expires_in": 3600,
        "scope": "openid profile",
        "token_type": "Bearer"
    }

    mock_client = MagicMock()
    mock_client.client_id = "test_client_id"

    mock_request = MagicMock(spec=OAuth2Request)
    mock_request.client = mock_client
    mock_request.user = {"id": 1}

    server.save_token(token_data, mock_request)

    server.save_token.assert_called_once_with(token_data, mock_request)


@pytest.mark.asyncio
async def test_save_token_without_user():
    """Проверка сохранения токена без пользователя (client credentials)."""
    server = await create_authorization_server()
    server.save_token = MagicMock()

    token_data = {
        "access_token": "client_token_123",
        "expires_in": 3600,
        "token_type": "Bearer"
    }

    mock_client = MagicMock()
    mock_client.client_id = "service_client"

    mock_request = MagicMock(spec=OAuth2Request)
    mock_request.client = mock_client
    mock_request.user = None

    server.save_token(token_data, mock_request)

    server.save_token.assert_called_once_with(token_data, mock_request)
