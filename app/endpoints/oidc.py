from auth.user_source import authenticate_user
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from templates_static import templates

router = APIRouter(prefix="/oidc", tags=["oidc"])


@router.get("/authorize")
async def authorize(request: Request):
    """Эндпоинт авторизации."""
    params = request.query_params
    return await request.app.state.oidc_server.authorize(
        request=request,
        client_id=params.get("client_id"),
        redirect_uri=params.get("redirect_uri"),
        response_type=params.get("response_type"),
        scope=params.get("scope", ""),
        state=params.get("state"),
    )


@router.get("/login")
async def login_page(request: Request):
    """Страница логина."""
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def login(request: Request):
    """Обработка логина."""
    form = await request.form()
    username = form.get("username")
    password = form.get("password")

    if not username or not password:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Введите логин и пароль"},
        )

    user = await authenticate_user(request, username, password)   # передаём request
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный логин или пароль"},
        )

    request.session["user"] = user

    oauth_params = request.session.pop("oauth_params", {})
    if oauth_params:
        redirect_url = f"/oidc/authorize?client_id={oauth_params['client_id']}&redirect_uri={oauth_params['redirect_uri']}&response_type=code&scope={oauth_params['scope']}"
        if oauth_params.get('state'):
            redirect_url += f"&state={oauth_params['state']}"
        return RedirectResponse(url=redirect_url)

    next_url = request.session.pop("next_url", "/")
    return RedirectResponse(url=next_url)


@router.post("/token")
async def token(request: Request):
    """Токен эндпоинт."""
    result = await request.app.state.oidc_server.token(request)
    return JSONResponse(result)


@router.get("/userinfo")
async def userinfo(request: Request):
    """Userinfo эндпоинт."""
    result = await request.app.state.oidc_server.userinfo(request)
    return JSONResponse(result)


@router.get("/jwks")
async def jwks(request: Request):
    """JWKS эндпоинт."""
    result = await request.app.state.oidc_server.jwks(request)
    return JSONResponse(result)


@router.get("/.well-known/openid-configuration")
async def openid_configuration(request: Request):
    """Discovery эндпоинт."""
    result = await request.app.state.oidc_server.openid_configuration(request)
    return JSONResponse(result)