"""Интеграционные тесты API пользователей."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_users_api(client: AsyncClient, setup_test_db):
    """Тест API списка пользователей."""
    response = await client.get("/admin/users/list")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_user_api(client: AsyncClient, setup_test_db):
    """Тест API создания пользователя."""
    user_data = {
        "username": "apiuser",
        "email": "api@test.com",
        "password": "secret123",
        "full_name": "API User",
        "is_active": True
    }
    response = await client.post("/admin/users/", json=user_data)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "apiuser"
    assert data["email"] == "api@test.com"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_user_duplicate_error(client: AsyncClient, setup_test_db):
    """Тест ошибки при создании дубликата пользователя."""
    user_data = {
        "username": "duplicate",
        "email": "dup@test.com",
        "password": "pass",
        "full_name": "First",
        "is_active": True
    }
    await client.post("/admin/users/", json=user_data)

    # Пытаемся создать с тем же username
    response = await client.post("/admin/users/", json=user_data)
    assert response.status_code == 400
    assert "Username already exists" in response.text


@pytest.mark.asyncio
async def test_get_user_api(client: AsyncClient, setup_test_db):
    """Тест API получения пользователя по ID."""
    # Сначала создаём
    create_resp = await client.post("/admin/users/", json={
        "username": "getuser",
        "email": "get@test.com",
        "password": "pass",
        "full_name": "Get User"
    })
    user_id = create_resp.json()["id"]

    # Получаем
    response = await client.get(f"/admin/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "getuser"
    assert data["email"] == "get@test.com"


@pytest.mark.asyncio
async def test_update_user_api(client: AsyncClient, setup_test_db):
    """Тест API обновления пользователя."""
    create_resp = await client.post("/admin/users/", json={
        "username": "updateuser",
        "email": "update@test.com",
        "password": "pass",
        "full_name": "Old Name"
    })
    user_id = create_resp.json()["id"]

    response = await client.put(f"/admin/users/{user_id}", json={
        "email": "new@test.com",
        "full_name": "New Name",
        "is_active": False
    })
    assert response.status_code == 200

    # Проверяем изменения
    get_resp = await client.get(f"/admin/users/{user_id}")
    assert get_resp.json()["email"] == "new@test.com"
    assert get_resp.json()["full_name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_user_api(client: AsyncClient, setup_test_db):
    """Тест API удаления пользователя."""
    create_resp = await client.post("/admin/users/", json={
        "username": "deleteuser",
        "email": "delete@test.com",
        "password": "pass",
        "full_name": "To Delete"
    })
    user_id = create_resp.json()["id"]

    response = await client.delete(f"/admin/users/{user_id}")
    assert response.status_code == 200

    # Проверяем что пользователь удалён
    get_resp = await client.get(f"/admin/users/{user_id}")
    assert get_resp.status_code == 404