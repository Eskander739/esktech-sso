"""Интеграционные тесты для OPAQUE токенов с реальной БД."""
import pytest
from constants import AccessTokenFormat
from db.oauth import OAuthTokenDB
from services.pool.db_pool import DBPool


@pytest.mark.asyncio
async def test_save_and_retrieve_opaque_token(setup_test_db):
    """Сохранение OPAQUE токена в БД и его получение."""
    db_pool = DBPool()
    await db_pool.create_tables()
    token_db = OAuthTokenDB(db_pool)

    token_value = "test_opaque_token_123"
    await token_db.save_token(
        token={"access_token": token_value, "expires_in": 3600},
        client_id="client1",
        user_id=1,
        scope="openid",
        token_type=AccessTokenFormat.OPAQUE,
    )

    record = await token_db.get_token_by_access(token_value)
    assert record is not None
    assert record["token_type"] == AccessTokenFormat.OPAQUE
    assert record["access_token"] == token_value
    assert record["is_revoked"] is False

    await db_pool.close_pool()


@pytest.mark.asyncio
async def test_revoke_opaque_token(setup_test_db):
    """Отзыв OPAQUE токена."""
    db_pool = DBPool()
    await db_pool.create_tables()
    token_db = OAuthTokenDB(db_pool)

    token_value = "revoke_me_opaque"
    await token_db.save_token(
        token={"access_token": token_value, "expires_in": 3600},
        client_id="client1",
        user_id=1,
        scope="openid",
        token_type=AccessTokenFormat.OPAQUE,
    )

    await token_db.revoke_access_token(token_value)
    record = await token_db.get_token_by_access(token_value)
    assert record is None  # revoked tokens not returned

    await db_pool.close_pool()