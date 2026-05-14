"""FastAPI приложение."""
from contextlib import asynccontextmanager
from typing import Any

from starlette.responses import RedirectResponse, JSONResponse
from starlette.staticfiles import StaticFiles

from constants import AccessTokenFormat, UserRole, ApiVersion
from models.msg import Message
from oidc_server import create_authorization_server
from config import settings
from db.oauth import OAuthClientDB, OAuthCodeDB, OAuthTokenDB
from db.users import UserDB
from endpoints.v0 import health, profile
from endpoints.oidc import oidc_api as oidc
from endpoints.v0.admin import users, clients
from fastapi import FastAPI, HTTPException, status, Request
from log import logger
from services.localization import _
from services.pool.db_pool import DBPool
from starlette.middleware.sessions import SessionMiddleware

from services.pool.redis_pool import RedisPoolManager
from services.redis_srv import RedisJWTManager
from utils.jwt import JWTService
from utils.password_validator import hash_password


async def ensure_admin_user(user_db):
    """Создать администратора если его нет."""
    admin_username = settings.ADMIN_USERNAME or "admin"
    admin_email = settings.ADMIN_EMAIL or "admin@localhost.local"
    admin_password = settings.ADMIN_PASSWORD or "Admin123!"

    existing_admin = await user_db.get_by_username(admin_username)

    if not existing_admin:
        hashed = hash_password(admin_password)
        user_id = await user_db.create(
            username=admin_username,
            email=admin_email,
            hashed_password=hashed,
            full_name="System Administrator",
            is_active=True,
            token_type=AccessTokenFormat.JWT,
            role=UserRole.SUPER_ADMIN
        )
        logger.info(f"✅ Администратор создан: {admin_username} (ID: {user_id})")
        logger.info(f"   Пароль: {admin_password} (сохраните и измените после первого входа!)")
    else:
        logger.info(f"ℹ️ Администратор уже существует: {admin_username}")


@asynccontextmanager
async def lifespan(app_local: Any):
    """Управление жизненным циклом приложения."""
    db_pool = DBPool()
    redis_pool = RedisPoolManager()
    await db_pool.create_tables()

    app_local.state.oidc_server = await create_authorization_server()
    app_local.state.db_pool = db_pool
    app_local.state.redis_pool = redis_pool
    app_local.state.oauth_client_db = OAuthClientDB(db_pool)
    app_local.state.oauth_code_db = OAuthCodeDB(db_pool)
    app_local.state.oauth_token_db = OAuthTokenDB(db_pool)
    app_local.state.user_db = UserDB(db_pool)
    await ensure_admin_user(app_local.state.user_db)
    app_local.state.redis_service = RedisJWTManager(app_local.state.redis_pool)
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


@app.middleware("http")
async def check_token(
    request: Request,
    call_next,
):
    """
    Проверяет токен на:

    1. Наличие его в cookie
    2. Что токен еще актуален
    3. Что токен имеется в Redis
    """

    if request.method == "OPTIONS":
        return await call_next(request)
    # Пропускаем проверку токена для эндпоинтов, которые не требуют аутентификации
    print("ААААААААААААААААААААААААААА", request.url.path)
    if request.url.path in [
        "/docs",
        "/openapi.json",
        "/login",
        f"{ApiVersion.V0}/users/logout",
        f"{ApiVersion.V0}/health",
        f"{ApiVersion.V0}/health/live",
        "/.well-known/appspecific/com.chrome.devtools.json"
        "/frontend/static/js/api.js"
        "/frontend/static/js/admin_client.js"
        "/frontend/static/js/login.js"
        "/frontend/static/js/profile.js"
    ] or "/login" in request.url.path or "/.well-known/appspecific/com.chrome.devtools.json" in request.url.path or request.url.path.count(".js") > 1 or request.url.path.count(".json") > 1:
        print("ББББББББББББББББББББББББББББББББ", request.url.path)
        return await call_next(request)

    access_token = request.cookies.get("session")
    jwt_service = JWTService()
    redis_service = RedisJWTManager(request.app.state.redis_pool)
    if not access_token:
        logger.info(
            f"- StatusCode: {status.HTTP_401_UNAUTHORIZED} - Body: {_(Message.token_not_found)}"
        )
        return RedirectResponse(
            status_code=status.HTTP_302_FOUND, url="/login")

    if not jwt_service.validate_token(access_token):
        logger.info(
            f"- StatusCode: {status.HTTP_401_UNAUTHORIZED} - Body: {_(Message.token_expired)}"
        )
        redirect_response = RedirectResponse(
            status_code=status.HTTP_302_FOUND, url="/login")
        redirect_response.delete_cookie(
            key="access_token", secure=True, httponly=True, samesite="lax"
        )
        return redirect_response
    if not await redis_service.is_token_valid(access_token):
        logger.info(
            f"- StatusCode: {status.HTTP_401_UNAUTHORIZED} - Body: {_(Message.token_invalid)}"
        )
        redirect_response = RedirectResponse(
            status_code=status.HTTP_302_FOUND, url="/login"
        )
        redirect_response.delete_cookie(
            key="access_token", secure=True, httponly=True, samesite="lax"
        )
        return redirect_response

    role = jwt_service.decode(access_token).get("role")
    print("Текущая роль: ", role)
    # TODO: Реализовать валидацию по ролевой модели

    response = await call_next(request)
    return response


app.mount("/frontend/static", StaticFiles(directory="frontend/static"), name="static")

app.include_router(health.router)
app.include_router(oidc.router)
app.include_router(profile.router)

# Admin section
app.include_router(users.router)
app.include_router(clients.router)


@app.get("/")
async def root():
    return RedirectResponse("/login")
