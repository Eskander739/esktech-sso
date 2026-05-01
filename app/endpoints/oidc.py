"""OIDC эндпоинты."""
from auth.user_source import authenticate_user
from fastapi import APIRouter, Request
from starlette.responses import RedirectResponse
from templates_static import templates

router = APIRouter(prefix="/oidc", tags=["oidc"])


@router.get("/authorize")
async def authorize(request: Request):
    """Эндпоинт авторизации OIDC."""
    user = request.session.get("user")
    if not user:
        request.session["next_url"] = str(request.url)
        return RedirectResponse(url="/oidc/login")
    return await request.app.state.oidc_server.create_authorize_response(request, user)


@router.get("/login")
async def login_page(request: Request):
    """Страница логина."""
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def login(request: Request):
    """Обработка формы логина."""
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    if not username or not password:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Введите логин и пароль"},
        )
    user = await authenticate_user(username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный логин или пароль"},
        )
    request.session["user"] = user
    next_url = request.session.pop("next_url", "/")
    return RedirectResponse(url=next_url)


@router.post("/token")
async def token(request: Request):
    """Эндпоинт для получения токенов."""
    return await request.app.state.oidc_server.create_token_response(request)


@router.get("/userinfo")
async def userinfo(request: Request):
    """Эндпоинт userinfo."""
    return await request.app.state.oidc_server.create_userinfo_response(request)


@router.get("/.well-known/openid-configuration")
async def openid_configuration(request: Request):
    """Discovery документ."""
    return await request.app.state.oidc_server.create_well_known_openid_configuration(request)


@router.get("/jwks")
async def jwks(request: Request):
    """Публичные JWK ключи."""
    return await request.app.state.oidc_server.create_jwks()
