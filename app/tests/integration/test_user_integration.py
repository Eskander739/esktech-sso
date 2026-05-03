"""Интеграционные тесты для пользователей."""
import pytest
from main import app
from sqlalchemy.exc import IntegrityError
from utils.password_validator import hash_password


@pytest.mark.asyncio
async def test_user_crud_flow():
    """Интеграционный тест полного CRUD цикла пользователя."""
    user_db = app.state.user_db

    # Создание
    hashed_password = hash_password("testpass123")
    user_id = await user_db.create(
        username="integration_user",
        email="integration@test.com",
        hashed_password=hashed_password,
        full_name="Integration Test",
        is_active=True
    )
    assert user_id is not None

    # Чтение по ID
    user = await user_db.get_by_id(user_id)
    assert user is not None
    assert user["username"] == "integration_user"
    assert user["email"] == "integration@test.com"
    assert user["full_name"] == "Integration Test"
    assert user["is_active"] is True

    # Чтение по username
    by_username = await user_db.get_by_username("integration_user")
    assert by_username is not None
    assert by_username["id"] == user_id

    # Чтение по email
    by_email = await user_db.get_by_email("integration@test.com")
    assert by_email is not None
    assert by_email["id"] == user_id

    # Обновление email
    await user_db.update_email(user_id, "updated@test.com")
    updated = await user_db.get_by_id(user_id)
    assert updated["email"] == "updated@test.com"

    # Обновление full_name
    await user_db.update_full_name(user_id, "Updated Name")
    updated = await user_db.get_by_id(user_id)
    assert updated["full_name"] == "Updated Name"

    # Обновление is_active
    await user_db.update_is_active(user_id, False)
    updated = await user_db.get_by_id(user_id)
    assert updated["is_active"] is False

    # Обновление пароля
    new_hashed = hash_password("newpassword123")
    await user_db.update_password(user_id, new_hashed)
    updated = await user_db.get_by_id(user_id)
    assert updated["hashed_password"] == new_hashed

    # Получение всех пользователей
    all_users = await user_db.get_all()
    assert len(all_users) >= 1
    assert any(u["id"] == user_id for u in all_users)

    # Удаление
    await user_db.delete(user_id)

    # Проверка что удалён
    gone = await user_db.get_by_id(user_id)
    assert gone is None


@pytest.mark.asyncio
async def test_create_duplicate_username():
    """Попытка создать пользователя с существующим username."""
    user_db = app.state.user_db

    # Создаём первого пользователя
    hashed = hash_password("pass")
    await user_db.create(
        username="unique_user",
        email="unique1@test.com",
        hashed_password=hashed,
        full_name="First User"
    )

    # Пытаемся создать с тем же username
    # Ожидаем ошибку уникальности
    try:
        await user_db.create(
            username="unique_user",
            email="unique2@test.com",
            hashed_password=hashed,
            full_name="Second User"
        )
        pytest.fail("Expected IntegrityError was not raised")
    except IntegrityError as e:
        # SQLAlchemy выбрасывает IntegrityError при дубликате
        assert "duplicate" in str(e).lower() or "UNIQUE" in str(e)


@pytest.mark.asyncio
async def test_create_duplicate_email():
    """Попытка создать пользователя с существующим email."""
    user_db = app.state.user_db

    # Создаём первого пользователя
    hashed = hash_password("pass")
    await user_db.create(
        username="user1",
        email="unique@test.com",
        hashed_password=hashed,
        full_name="First User"
    )

    # Пытаемся создать с тем же email
    try:
        await user_db.create(
            username="user2",
            email="unique@test.com",
            hashed_password=hashed,
            full_name="Second User"
        )
        pytest.fail("Expected IntegrityError was not raised")
    except IntegrityError as e:
        assert "duplicate" in str(e).lower() or "UNIQUE" in str(e)


@pytest.mark.asyncio
async def test_get_by_username_and_email():
    """Тест поиска по username и email."""
    user_db = app.state.user_db

    # Создаём пользователя
    hashed = hash_password("pass")
    user_id = await user_db.create(
        username="search_user",
        email="search@test.com",
        hashed_password=hashed,
        full_name="Search Me"
    )

    # Поиск по username
    by_username = await user_db.get_by_username("search_user")
    assert by_username is not None
    assert by_username["id"] == user_id
    assert by_username["email"] == "search@test.com"

    # Поиск по email
    by_email = await user_db.get_by_email("search@test.com")
    assert by_email is not None
    assert by_email["id"] == user_id
    assert by_email["username"] == "search_user"

    # Поиск несуществующего
    not_found_username = await user_db.get_by_username("does_not_exist")
    assert not_found_username is None

    not_found_email = await user_db.get_by_email("doesnotexist@test.com")
    assert not_found_email is None

    # Чистим
    await user_db.delete(user_id)

    # Проверка что удалён
    deleted = await user_db.get_by_id(user_id)
    assert deleted is None
