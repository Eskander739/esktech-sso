"""FastAPI приложение."""
from contextlib import asynccontextmanager
from typing import Any

from starlette.responses import RedirectResponse

from auth_server import create_authorization_server
from config import settings
from constants import ApiVersion
from db.oauth import OAuthClientDB, OAuthCodeDB, OAuthTokenDB
from db.users import UserDB
from endpoints.v0 import health, oidc
from endpoints.v0.admin import users, clients
from fastapi import FastAPI
from log import logger
from services.db_pool import DBPool
from starlette.middleware.sessions import SessionMiddleware


@asynccontextmanager
async def lifespan(app_local: Any):
    """Управление жизненным циклом приложения."""
    db_pool = DBPool()
    await db_pool.create_tables()

    app_local.state.oidc_server = await create_authorization_server()
    app_local.state.db_pool = db_pool
    app_local.state.oauth_client_db = OAuthClientDB(db_pool)
    app_local.state.oauth_code_db = OAuthCodeDB(db_pool)
    app_local.state.oauth_token_db = OAuthTokenDB(db_pool)
    app_local.state.user_db = UserDB(db_pool)
    app_local.state.logger = logger
    app_local.state.ldap_uri = settings.LDAP_URI

    yield
    if hasattr(app_local.state, "db_pool"):
        await app_local.state.db_pool.close_pool()



app = FastAPI(
    title="EskTech SSO",
    description="Open Source SSO сервер на Python",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)


app.include_router(health.router)
app.include_router(oidc.router)
# Admin section

app.include_router(users.router)
app.include_router(clients.router)


@app.get("/")
async def root():
    print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", settings.ISSUER)
    return RedirectResponse(f"{ApiVersion.V0}/login")