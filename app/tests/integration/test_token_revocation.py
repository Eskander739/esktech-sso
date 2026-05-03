"""Интеграционные тесты для отзыва токенов."""
import pytest
from constants import AccessTokenFormat
from db.oauth import OAuthTokenDB
from services.db_pool import DBPool


@pytest.mark.asyncio
async def test_revoke_access_token(setup_test_db):
    """Отзыв access токена через БД."""
    db_pool = DBPool()
    await db_pool.create_tables()
    token_db = OAuthTokenDB(db_pool)

    # Сохраняем токен
    token_value = "test_access_revoke_123"
    await token_db.save_token(
        token={"access_token": token_value, "expires_in": 3600},
        client_id="client1",
        user_id=1,
        scope="openid",
        token_type=AccessTokenFormat.OPAQUE,
    )

    # Проверяем что существует
    record = await token_db.get_token_by_access(token_value)
    assert record is not None

    # Отзываем
    await token_db.revoke_access_token(token_value)

    # Проверяем что не возвращается
    revoked = await token_db.get_token_by_access(token_value)
    assert revoked is None

    await db_pool.close_pool()


@pytest.mark.asyncio
async def test_revoke_refresh_token(setup_test_db):
    """Отзыв refresh токена через БД."""
    db_pool = DBPool()
    await db_pool.create_tables()
    token_db = OAuthTokenDB(db_pool)

    # Сохраняем токен с refresh
    refresh_value = "test_refresh_revoke_123"
    await token_db.save_token(
        token={"access_token": "at123", "expires_in": 3600},
        client_id="client1",
        user_id=1,
        scope="openid",
        refresh_token=refresh_value,
        token_type=AccessTokenFormat.OPAQUE,
    )

    # Проверяем что существует
    record = await token_db.get_token_by_refresh(refresh_value)
    assert record is not None

    # Отзываем
    await token_db.revoke_token(refresh_value)

    # Проверяем что не возвращается
    revoked = await token_db.get_token_by_refresh(refresh_value)
    assert revoked is None

    await db_pool.close_pool()