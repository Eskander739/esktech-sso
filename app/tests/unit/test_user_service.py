"""Unit тесты для сервиса пользователей."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from db.models import User
from services.user_service import UserService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_all_users():
    """Тест получения всех пользователей."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.username = "testuser"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_user]
    mock_session.execute.return_value = mock_result

    service = UserService(mock_session)
    users = await service.get_all()

    assert len(users) == 1
    assert users[0].username == "testuser"


@pytest.mark.asyncio
async def test_get_user_by_id_found():
    """Тест получения пользователя по ID (найден)."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.username = "testuser"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    service = UserService(mock_session)
    user = await service.get_by_id(1)

    assert user is not None
    assert user.id == 1


@pytest.mark.asyncio
async def test_get_user_by_id_not_found():
    """Тест получения пользователя по ID (не найден)."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    service = UserService(mock_session)
    user = await service.get_by_id(999)

    assert user is None


@pytest.mark.asyncio
async def test_create_user():
    """Тест создания пользователя."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.add = MagicMock()  # синхронный метод
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    with patch("services.user_service.hash_password", return_value="hashed_pass"):
        service = UserService(mock_session)
        user = await service.create(
            username="newuser",
            email="new@example.com",
            password="secret123",
            full_name="New User",
            is_active=True
        )

        assert user.username == "newuser"
        assert user.email == "new@example.com"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

@pytest.mark.asyncio
async def test_update_user_success():
    """Тест успешного обновления пользователя."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.email = "old@example.com"
    mock_user.full_name = "Old Name"
    mock_user.is_active = True

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    with patch("services.user_service.hash_password", return_value="new_hashed"):
        service = UserService(mock_session)
        user = await service.update(
            user_id=1,
            email="new@example.com",
            full_name="New Name",
            is_active=False
        )

        assert user.email == "new@example.com"
        assert user.full_name == "New Name"
        assert user.is_active is False
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_not_found():
    """Тест обновления несуществующего пользователя."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    service = UserService(mock_session)
    user = await service.update(user_id=999, email="test@example.com")

    assert user is None


@pytest.mark.asyncio
async def test_delete_user_success():
    """Тест успешного удаления пользователя."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_user = MagicMock(spec=User)
    mock_user.id = 1

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    service = UserService(mock_session)
    result = await service.delete(1)

    assert result is True
    mock_session.delete.assert_called_once_with(mock_user)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_user_not_found():
    """Тест удаления несуществующего пользователя."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    service = UserService(mock_session)
    result = await service.delete(999)

    assert result is False
    mock_session.delete.assert_not_called()


@pytest.mark.asyncio
async def test_check_exists():
    """Тест проверки существования пользователя."""
    mock_session = AsyncMock(spec=AsyncSession)

    # Имитируем что пользователь существует
    mock_result_username = MagicMock()
    mock_result_username.scalar_one_or_none.return_value = MagicMock(spec=User)
    mock_result_email = MagicMock()
    mock_result_email.scalar_one_or_none.return_value = None

    mock_session.execute.side_effect = [mock_result_username, mock_result_email]

    service = UserService(mock_session)
    username_exists, email_exists = await service.check_exists("existing", "new@example.com")

    assert username_exists is True
    assert email_exists is False