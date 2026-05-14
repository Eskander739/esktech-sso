"""Административные эндпоинты (управление OIDC клиентами)."""
import secrets

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import ProgrammingError

from constants import ApiVersion
from models.general import ClientCreate, RevokeTokenRequest
from frontend.templates import templates

router = APIRouter(prefix=f"{ApiVersion.V0}/admin", tags=["admin"])


@router.get("/clients", response_class=HTMLResponse)
async def admin_clients(request: Request):
    """Страница управления клиентами (простая админка)."""
    return templates.TemplateResponse(request, "admin_clients.html")


@router.post("/clients")
async def create_client(request: Request, data: ClientCreate):
    """Создание нового OAuth2/OIDC клиента."""

    client_id = secrets.token_urlsafe(16)
    client_secret = secrets.token_urlsafe(32)

    oauth_client_db = request.app.state.oauth_client_db
    await oauth_client_db.create_client(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uris=data.redirect_uris,
        application_name=data.name,
    )
    return {"client_id": client_id, "client_secret": client_secret}

@router.get("/clients/list")
async def list_clients(request: Request):
    """Получение списка всех OIDC клиентов."""
    oauth_client_db = request.app.state.oauth_client_db
    clients = await oauth_client_db.get_all_clients()
    return clients


@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(request: Request, client_id: str):
    """Удаление OIDC клиента."""
    try:
        oauth_client_db = request.app.state.oauth_client_db
        oauth_token_db = request.app.state.oauth_token_db  # добавьте

        client = await oauth_client_db.get_client_by_id(int(client_id))
        if client:
            await oauth_token_db.revoke_all_client_tokens(client["client_id"])

        await oauth_client_db.delete_client_by_id(client_id)

    except ProgrammingError as err:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(err))

@router.post("/revoke")
async def revoke_token(request: Request, data: RevokeTokenRequest):
    """Отозвать конкретный токен (access или refresh)"""
    oauth_token_db = request.app.state.oauth_token_db

    if data.token_type == "access":
        await oauth_token_db.revoke_access_token(data.token)
    else:
        await oauth_token_db.revoke_token(data.token)  # revoke_token отзывает refresh

    return {"message": "Token revoked successfully"}


@router.post("/revoke/user/{user_id}")
async def revoke_user_tokens(request: Request, user_id: int, exclude_current: bool = True):
    """Отозвать все токены пользователя"""
    oauth_token_db = request.app.state.oauth_token_db
    current_token = None

    if exclude_current:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            current_token = auth_header[7:]

    revoked_count = await oauth_token_db.revoke_all_user_tokens(
        user_id=user_id,
        exclude_access_token=current_token
    )

    return {
        "message": f"Revoked {revoked_count} tokens for user {user_id}",
        "revoked_count": revoked_count
    }


@router.get("/user/active")
async def get_my_tokens(request: Request):
    """Получить все активные токены текущего пользователя"""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    oauth_token_db = request.app.state.oauth_token_db
    tokens = await oauth_token_db.get_user_active_tokens(user["id"])

    return {"user_id": user["id"], "active_tokens": tokens}


@router.get("/users/{user_id}/tokens")
async def get_user_tokens(request: Request, user_id: int):
    """Получить список активных токенов пользователя (админ)."""
    oauth_token_db = request.app.state.oauth_token_db
    tokens = await oauth_token_db.get_user_active_tokens(user_id)
    return tokens


@router.post("/users/{user_id}/tokens/revoke")
async def revoke_user_tokens_admin(
    request: Request,
    user_id: int,
    data: RevokeTokenRequest = None
):
    """
    Отозвать токены пользователя.
    Если data.token передан – отзываем конкретный токен (access или refresh).
    Если нет – отзываем все токены пользователя.
    """
    oauth_token_db = request.app.state.oauth_token_db
    if data and data.token:
        if data.token_type == "access":
            await oauth_token_db.revoke_access_token(data.token)
        else:
            await oauth_token_db.revoke_token(data.token)
        return {"message": "Token revoked"}
    else:
        revoked = await oauth_token_db.revoke_all_user_tokens(user_id)
        return {"message": f"Revoked {revoked} tokens"}
