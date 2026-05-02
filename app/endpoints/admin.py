"""Административные эндпоинты (управление OIDC клиентами)."""
import secrets

from config import settings
from db.crud import create_oauth_client
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from templates_static import templates
from utils.license import is_enterprise
from utils.limits import check_clients_limit

router = APIRouter()


class ClientCreate(BaseModel):
    name: str
    redirect_uris: str


@router.get("/clients", response_class=HTMLResponse)
async def admin_clients(request: Request):
    """Страница управления клиентами (простая админка)."""
    return templates.TemplateResponse(request, "admin_clients.html")


@router.post("/clients")
async def create_client(data: ClientCreate):
    """Создание нового OAuth2/OIDC клиента."""
    if not is_enterprise(settings.LICENSE_KEY) and not await check_clients_limit():
        raise HTTPException(status_code=403, detail="Community лимит: не более 2 клиентов")
    client_id = secrets.token_urlsafe(16)
    client_secret = secrets.token_urlsafe(32)
    await create_oauth_client(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uris=data.redirect_uris,
        application_name=data.name,
    )
    return {"client_id": client_id, "client_secret": client_secret}
