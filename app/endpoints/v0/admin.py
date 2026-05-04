"""Административные эндпоинты (управление OIDC клиентами)."""
import secrets

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from models.general import ClientCreate
from templates_static import templates

router = APIRouter()


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