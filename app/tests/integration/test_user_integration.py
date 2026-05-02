# app/tests/integration/test_user_integration.py
"""Интеграционные тесты для пользователей."""
import pytest
from services.user_service import UserService
from sqlalchemy.exc import IntegrityError


@pytest.mark.asyncio
async def test_user_crud_flow(db_session):
    """Интеграционный тест полного CRUD цикла пользователя."""
    session = db_session
    service = UserService(session)

    # Создание
    user = await service.create(
        username="integration_user",
        email="integration@test.com",
        password="testpass123",
        full_name="Integration Test",
        is_active=True
    )
    assert user.id is not None
    assert user.username == "integration_user"

    # Чтение
    found = await service.get_by_id(user.id)
    assert found is not None
    assert found.email == "integration@test.com"

    # Обновление
    updated = await service.update(
        user_id=user.id,
        email="updated@test.com",
        full_name="Updated Name",
        is_active=False
    )
    assert updated.email == "updated@test.com"
    assert updated.full_name == "Updated Name"
    assert updated.is_active is False

    # Удаление
    deleted = await service.delete(user.id)
    assert deleted is True

    # Проверка что удалён
    gone = await service.get_by_id(user.id)
    assert gone is None


@pytest.mark.asyncio
async def test_create_duplicate_username(db_session):
    """Попытка создать пользователя с существующим username."""
    session = db_session
    service = UserService(session)

    await service.create(
        username="unique_user",
        email="unique1@test.com",
        password="pass"
    )

    with pytest.raises(IntegrityError):
        await service.create(
            username="unique_user",
            email="unique2@test.com",
            password="pass"
        )

    await session.rollback()


@pytest.mark.asyncio
async def test_create_duplicate_email(db_session):
    """Попытка создать пользователя с существующим email."""
    session = db_session
    service = UserService(session)

    await service.create(
        username="user1",
        email="unique@test.com",
        password="pass"
    )

    with pytest.raises(IntegrityError):
        await service.create(
            username="user2",
            email="unique@test.com",
            password="pass"
        )

    await session.rollback()

@pytest.mark.asyncio
async def test_get_by_username_and_email(db_session):
    """Тест поиска по username и email."""
    session = db_session
    service = UserService(session)

    user = await service.create(
        username="search_user",
        email="search@test.com",
        password="pass",
        full_name="Search Me"
    )

    by_username = await service.get_by_username("search_user")
    assert by_username is not None
    assert by_username.email == "search@test.com"

    by_email = await service.get_by_email("search@test.com")
    assert by_email is not None
    assert by_email.username == "search_user"

    not_found = await service.get_by_username("does_not_exist")
    assert not_found is None

    # Чистим
    await service.delete(user.id)