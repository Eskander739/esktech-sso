from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import Request
from utils.limits import check_clients_limit, count_oauth_clients


@pytest.mark.asyncio
async def test_clients_limit_community():
    """Тест лимита клиентов для Community версии."""
    # Создаём мок request
    request = Mock(spec=Request)

    # Создаём мок для oauth_client_db
    mock_client_db = AsyncMock()
    mock_client_db.count_active_clients = AsyncMock(return_value=1)

    # Привязываем к request.app.state
    request.app = Mock()
    request.app.state.oauth_client_db = mock_client_db

    # Проверяем count_oauth_clients
    count = await count_oauth_clients(request)
    assert count == 1

    # Проверяем check_clients_limit
    is_within_limit = await check_clients_limit(request)
    assert is_within_limit is True  # 1 < 2

    # Меняем количество на 2
    mock_client_db.count_active_clients = AsyncMock(return_value=2)
    is_within_limit = await check_clients_limit(request)
    assert is_within_limit is False  # 2 < 2 - false


@pytest.mark.asyncio
async def test_clients_limit_enterprise():
    """Тест лимита клиентов для Enterprise версии."""
    # Создаём мок request
    request = Mock(spec=Request)

    # Создаём мок для oauth_client_db
    mock_client_db = AsyncMock()
    mock_client_db.count_active_clients = AsyncMock(return_value=100)

    # Привязываем к request.app.state
    request.app = Mock()
    request.app.state.oauth_client_db = mock_client_db

    # Для enterprise лимит не проверяется (в реальном коде проверка через is_enterprise)
    # Здесь просто проверяем, что функция работает с большим числом
    count = await count_oauth_clients(request)
    assert count == 100
