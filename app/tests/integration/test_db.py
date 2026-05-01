import random

import pytest
from db.crud import create_user, get_user_by_username
from db.database import close_db, init_db


@pytest.mark.asyncio
async def test_create_and_get_user():
    await init_db()
    username = f"testuser{random.randint(10000, 99999)}"
    await create_user(username, f"test{random.randint(10000, 99999)}@example.com", "hashed", "Test User")
    user = await get_user_by_username(username)
    assert user is not None
    assert user["username"] == username
    await close_db()
