from unittest.mock import AsyncMock, patch

import pytest
from config import settings
from utils.limits import check_clients_limit


@pytest.mark.asyncio
async def test_clients_limit_community():
    with patch("utils.limits.count_oauth_clients", AsyncMock(return_value=2)):
        settings.LICENSE_KEY = ""
        settings.COMMUNITY_MAX_CLIENTS = 2
        assert await check_clients_limit() is False
    with patch("utils.limits.count_oauth_clients", AsyncMock(return_value=1)):
        assert await check_clients_limit() is True


@pytest.mark.asyncio
async def test_clients_limit_enterprise():
    with patch("utils.limits.count_oauth_clients", AsyncMock(return_value=10)):
        settings.LICENSE_KEY = "ESKTECH-ENTERPRISE-2026"
        assert await check_clients_limit() is True
