from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from models.msg import Message
from services.localization import _
from templates_static import templates
from utils.user_source import authenticate_user

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
            {"request": request, "error": _(Message.input_login_and_password)},
        )

    user = await authenticate_user(request, username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": _(Message.invalid_password_or_login)},
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


@router.post("/revoke")
async def revoke_token(request: Request):
    """OAuth 2.0 Token Revocation endpoint (RFC 7009)."""
    form = await request.form()
    token = form.get("token")
    token_type_hint = form.get("token_type_hint", "access_token")

    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _(Message.token_not_found))

    # Basic аутентификация клиента
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Basic "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _(Message.missing_or_invalid_client_credentials))

    import base64
    credentials = base64.b64decode(auth[6:]).decode()
    client_id, client_secret = credentials.split(":", 1)

    # Проверяем клиента
    client = await request.app.state.oauth_client_db.get_client(client_id)
    if not client or client.get("client_secret") != client_secret:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _(Message.invalid_client_credentials))

    oauth_token_db = request.app.state.oauth_token_db

    if token_type_hint == "access_token":
        await oauth_token_db.revoke_access_token(token)
    elif token_type_hint == "refresh_token":
        await oauth_token_db.revoke_token(token)
    else:
        # Пробуем оба варианта
        await oauth_token_db.revoke_access_token(token)
        await oauth_token_db.revoke_token(token)

    return {"message": _(Message.token_revoked)}



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