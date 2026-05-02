import random

import pytest
from main import app


@pytest.mark.asyncio
async def test_create_and_get_user():
    """Тест создания и получения пользователя через глобальные фикстуры."""
    user_db = app.state.user_db

    # Генерируем случайные данные
    username = f"testuser{random.randint(10000, 99999)}"
    email = f"test{random.randint(10000, 99999)}@example.com"

    # Создаём пользователя
    user_id = await user_db.create(
        username=username,
        email=email,
        hashed_password="hashed_password_here",
        full_name="Test User",
        is_active=True
    )

    # Получаем пользователя по username
    user = await user_db.get_by_username(username)

    # Проверяем
    assert user is not None
    assert user["username"] == username
    assert user["email"] == email
    assert user["full_name"] == "Test User"
    assert user["is_active"] is True

    # Получаем пользователя по ID
    user_by_id = await user_db.get_by_id(user_id)
    assert user_by_id is not None
    assert user_by_id["id"] == user_id
    assert user_by_id["username"] == username