# app/endpoints/users.py
"""Управление пользователями (CRUD) для администратора."""

from auth.password_validator import hash_password
from db.database import get_session
from db.models import User
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from templates_static import templates

router = APIRouter(prefix="/admin/users", tags=["admin"])


# ---------- Модели для API ----------
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: str | None = None
    is_active: bool = True


class UserUpdate(BaseModel):
    email: str | None = None
    password: str | None = None
    full_name: str | None = None
    is_active: bool | None = None


# ---------- HTML страницы ----------
@router.get("/", response_class=HTMLResponse)
async def list_users_html(request: Request, session: AsyncSession = Depends(get_session)):
    """Список пользователей (админка)."""
    result = await session.execute(select(User))
    users = result.scalars().all()
    return templates.TemplateResponse(request, "admin_users.html", {"users": users})


@router.get("/create", response_class=HTMLResponse)
async def create_user_form(request: Request):
    """Форма создания пользователя."""
    return templates.TemplateResponse(request, "admin_user_form.html", {"user": None})


@router.get("/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_form(request: Request, user_id: int, session: AsyncSession = Depends(get_session)):
    """Форма редактирования пользователя."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return templates.TemplateResponse(request, "admin_user_form.html", {"user": user})


# ---------- JSON API (должны быть ПЕРЕД маршрутами с {user_id}) ----------
@router.get("/list", response_model=list[dict])
async def list_users_json(session: AsyncSession = Depends(get_session)):
    """Список пользователей в JSON (для админки)."""
    result = await session.execute(select(User))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


# ---------- CRUD API (REST) ----------
@router.post("/", response_model=dict)
async def create_user(data: UserCreate, session: AsyncSession = Depends(get_session)):
    """Создать пользователя."""
    # Проверка уникальности
    result = await session.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")
    result = await session.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already exists")

    hashed = hash_password(data.password) if data.password else None
    new_user = User(
        username=data.username,
        email=data.email,
        hashed_password=hashed,
        full_name=data.full_name,
        is_active=data.is_active,
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return {"id": new_user.id, "username": new_user.username, "email": new_user.email}


@router.get("/{user_id}", response_model=dict)
async def get_user(user_id: int, session: AsyncSession = Depends(get_session)):
    """Получить пользователя по ID."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "uuid": str(user.uuid),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


@router.put("/{user_id}")
async def update_user(user_id: int, data: UserUpdate, session: AsyncSession = Depends(get_session)):
    """Обновить пользователя."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.email is not None:
        existing = await session.execute(
            select(User).where(User.email == data.email, User.id != user_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already exists")
        user.email = data.email
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.password:
        user.hashed_password = hash_password(data.password)

    await session.commit()
    return {"message": "User updated"}


@router.delete("/{user_id}")
async def delete_user(user_id: int, session: AsyncSession = Depends(get_session)):
    """Удалить пользователя."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await session.delete(user)
    await session.commit()
    return {"message": "User deleted"}