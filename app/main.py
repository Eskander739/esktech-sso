"""FastAPI приложение."""
from contextlib import asynccontextmanager
from typing import Any

from auth_server import create_authorization_server
from config import settings
from db.database import close_db, init_db
from endpoints import admin, health, oidc
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware


@asynccontextmanager
async def lifespan(app_local: Any):
    """Управление жизненным циклом приложения."""
    app_local.state.oidc_server = await create_authorization_server()
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="EskTech SSO",
    description="Open Source SSO сервер на Python",
    version="0.1.0",
    lifespan=lifespan,
)

# Сессионная middleware (для страницы логина)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Подключение роутеров
app.include_router(health.router)
app.include_router(oidc.router)
app.include_router(admin.router, prefix="/admin", tags=["admin"])


@app.get("/")
async def root():
    return {"message": "EskTech SSO сервер работает"}
