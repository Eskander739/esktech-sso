"""Профиль пользователя (личный кабинет)."""
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from models.msg import Message
from models.users import UserUpdateProfile, UserChangePassword
from services.localization import _
from utils.password_validator import hash_password, validate_password_strength
from frontend.templates import templates
from constants import ApiVersion

router = APIRouter(prefix=f"{ApiVersion.V0}/profile", tags=["profile"])


@router.get("/", response_class=HTMLResponse)
async def profile_page(request: Request):
    """Страница профиля пользователя."""
    user = request.session.get("user")
    if not user:
        request.session["next_url"] = f"{ApiVersion.V0}/profile"
        return templates.TemplateResponse(request, "login.html")

    return templates.TemplateResponse(request, "profile.html")


@router.get("/data")
async def get_profile_data(request: Request):
    """Получить данные текущего пользователя (JSON)."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_(Message.not_authenticated))

    user_db = request.app.state.user_db
    full_user = await user_db.get_by_id(user["id"])

    if not full_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_(Message.user_not_found))

    return {
        "id": full_user["id"],
        "username": full_user["username"],
        "email": full_user["email"],
        "full_name": full_user.get("full_name", ""),
        "is_active": full_user.get("is_active", True),
        "created_at": full_user.get("created_at"),
        "token_type": full_user.get("token_type", "jwt")
    }


@router.put("/data")
async def update_profile_data(request: Request, data: UserUpdateProfile):
    """Обновить данные профиля."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_(Message.not_authenticated))

    user_db = request.app.state.user_db
    user_id = user["id"]

    # Проверяем существование пользователя
    existing_user = await user_db.get_by_id(user_id)
    if not existing_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_(Message.user_not_found))

    # Обновляем email (проверяем уникальность)
    if data.email is not None and data.email != existing_user["email"]:
        await user_db.update_email(user_id, data.email)
        # Обновляем email в сессии
        user["email"] = data.email
        request.session["user"] = user

    # Обновляем полное имя
    if data.full_name is not None:
        await user_db.update_full_name(user_id, data.full_name)
        user["full_name"] = data.full_name
        request.session["user"] = user

    return {"message": _(Message.profile_updated)}


@router.put("/change-password")
async def change_password(request: Request, data: UserChangePassword):
    """Сменить пароль."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_(Message.not_authenticated))

    user_db = request.app.state.user_db
    user_id = user["id"]
    existing_user = await user_db.get_by_id(user_id)

    if not existing_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_(Message.user_not_found))

    # Проверяем старый пароль (если пользователь не из LDAP)
    if existing_user.get("hashed_password"):
        from utils.password_validator import verify_password
        if not verify_password(data.old_password, existing_user["hashed_password"]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_(Message.invalid_old_password))

    # Валидация нового пароля
    if not validate_password_strength(data.new_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_(Message.password_too_weak))

    # Обновляем пароль
    hashed = hash_password(data.new_password)
    await user_db.update_password(user_id, hashed)

    # Отзываем все токены пользователя (кроме текущей сессии)
    oauth_token_db = request.app.state.oauth_token_db
    await oauth_token_db.revoke_all_user_tokens(user_id)

    return {"message": _(Message.password_changed)}


@router.get("/tokens")
async def get_my_tokens(request: Request):
    """Получить активные токены текущего пользователя."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_(Message.not_authenticated))

    oauth_token_db = request.app.state.oauth_token_db
    tokens = await oauth_token_db.get_user_active_tokens(user["id"])

    return {"tokens": tokens}


@router.post("/tokens/revoke")
async def revoke_my_token(request: Request, token: str, token_type: str = "access"):
    """Отозвать конкретный токен текущего пользователя."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_(Message.not_authenticated))

    oauth_token_db = request.app.state.oauth_token_db

    if token_type == "access":
        await oauth_token_db.revoke_access_token(token)
    else:
        await oauth_token_db.revoke_token(token)

    return {"message": _(Message.token_revoked)}


@router.post("/tokens/revoke-all")
async def revoke_all_my_tokens(request: Request):
    """Отозвать все токены текущего пользователя (кроме текущей сессии)."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_(Message.not_authenticated))

    oauth_token_db = request.app.state.oauth_token_db

    auth_header = request.headers.get("Authorization")
    current_token = auth_header[7:] if auth_header and auth_header.startswith("Bearer ") else None

    revoked_count = await oauth_token_db.revoke_all_user_tokens(
        user_id=user["id"],
        exclude_access_token=current_token
    )

    return {"message": _(Message.all_tokens_revoked).format(count=revoked_count)}