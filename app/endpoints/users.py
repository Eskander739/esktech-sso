"""Управление пользователями (CRUD) для администратора."""
from auth.password_validator import hash_password
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from templates_static import templates

router = APIRouter(prefix="/admin/users", tags=["admin"])


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
async def list_users_html(request: Request):
    """Список пользователей (админка)."""
    user_db = request.app.state.user_db
    users = await user_db.get_all()  # нужно добавить метод get_all в UserDB
    return templates.TemplateResponse(request, "admin_users.html", {"users": users})


@router.get("/create", response_class=HTMLResponse)
async def create_user_form(request: Request):
    """Форма создания пользователя."""
    return templates.TemplateResponse(request, "admin_user_form.html", {"user": None})


@router.get("/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_form(request: Request, user_id: int):
    """Форма редактирования пользователя."""
    user_db = request.app.state.user_db
    user = await user_db.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return templates.TemplateResponse(request, "admin_user_form.html", {"user": user})


# ---------- JSON API ----------
@router.get("/list", response_model=list[dict])
async def list_users_json(request: Request):
    """Список пользователей в JSON (для админки)."""
    user_db = request.app.state.user_db
    users = await user_db.get_all()
    return [
        {
            "id": u["id"],
            "username": u["username"],
            "email": u["email"],
            "full_name": u["full_name"],
            "is_active": u["is_active"],
            "created_at": u.get("created_at"),
        }
        for u in users
    ]


@router.post("/", response_model=dict)
async def create_user(request: Request, data: UserCreate):
    """Создать пользователя."""
    user_db = request.app.state.user_db
    # Проверка уникальности
    existing = await user_db.get_by_username(data.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    existing = await user_db.get_by_email(data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    hashed = hash_password(data.password) if data.password else None
    user_id = await user_db.create(
        username=data.username,
        email=data.email,
        hashed_password=hashed,
        full_name=data.full_name,
        is_active=data.is_active,
    )
    return {"id": user_id, "username": data.username, "email": data.email}


@router.get("/{user_id}", response_model=dict)
async def get_user(request: Request, user_id: int):
    """Получить пользователя по ID."""
    user_db = request.app.state.user_db
    user = await user_db.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}")
async def update_user(request: Request, user_id: int, data: UserUpdate):
    """Обновить пользователя."""
    user_db = request.app.state.user_db
    user = await user_db.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.email is not None:
        existing = await user_db.get_by_email(data.email)
        if existing and existing["id"] != user_id:
            raise HTTPException(status_code=400, detail="Email already exists")
        await user_db.update_email(user_id, data.email)
    if data.full_name is not None:
        await user_db.update_full_name(user_id, data.full_name)
    if data.is_active is not None:
        await user_db.update_is_active(user_id, data.is_active)
    if data.password:
        hashed = hash_password(data.password)
        await user_db.update_password(user_id, hashed)

    return {"message": "User updated"}


@router.delete("/{user_id}")
async def delete_user(request: Request, user_id: int):
    """Удалить пользователя."""
    user_db = request.app.state.user_db
    user = await user_db.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await user_db.delete(user_id)
    return {"message": "User deleted"}