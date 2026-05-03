"""Управление пользователями (CRUD) для администратора."""
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from models.msg import Message
from models.users import UserCreate, UserUpdate
from services.localization import _
from templates_static import templates
from utils.password_validator import hash_password

router = APIRouter(prefix="/admin/users", tags=["admin"])


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_(Message.user_not_found))
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
    user = await user_db.get_by_username(data.username)
    if user or user is not None and user.get("email") == data.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_(Message.user_is_already_registered))

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_(Message.user_not_found))
    return user


@router.put("/{user_id}")
async def update_user(request: Request, user_id: int, data: UserUpdate):
    """Обновить пользователя."""
    user_db = request.app.state.user_db
    user = await user_db.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_(Message.user_not_found))

    if data.email is not None:
        existing = await user_db.get_by_email(data.email)
        if existing and existing["id"] != user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_(Message.user_is_already_registered))
        await user_db.update_email(user_id, data.email)
    if data.full_name is not None:
        await user_db.update_full_name(user_id, data.full_name)
    if data.is_active is not None:
        await user_db.update_is_active(user_id, data.is_active)
    if data.password:
        hashed = hash_password(data.password)
        await user_db.update_password(user_id, hashed)

    return {"message": _(Message.user_is_not_updated)}


@router.delete("/{user_id}")
async def delete_user(request: Request, user_id: int):
    """Удалить пользователя."""
    user_db = request.app.state.user_db
    user = await user_db.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_(Message.user_not_found))
    await user_db.delete(user_id)
    return {"message": _(Message.user_is_deleted)}
