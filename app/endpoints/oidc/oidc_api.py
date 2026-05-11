from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from models.msg import Message
from services.localization import _
from services.sources import authenticate_from_sources
from templates_static import templates

router = APIRouter(tags=["oidc"])


"""
См пример работы:

1. Пользователь в Jira нажимает "Войти через EskTech"
   ↓
2. Jira редиректит браузер на:
   https://sso.esktech.ru/authorize?client_id=xxx&redirect_uri=https://jira/callback&response_type=code
   ↓
3. Ваш SSO проверяет сессию → нет сессии → редирект на /login
   ↓
4. Пользователь видит вашу login.html → вводит логин/пароль
   ↓
5. POST /login → проверка пароля → создание сессии
   ↓
6. Ваш SSO достаёт oauth_params (сохранённые из шага 2) и редиректит обратно на /authorize
   ↓
7. Теперь сессия есть → authorize генерирует code → редирект на redirect_uri (Jira):
   https://jira.example.com/callback?code=abc123
   ↓
8. Jira получает code → отправляет POST /oidc/token со своим client_secret
   ↓
9. Ваш SSO выдаёт access_token, refresh_token, id_token
   ↓
10. Jira может запросить /userinfo с access_token, чтобы получить данные пользователя
"""
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
        nonce=params.get("nonce"),
    )


@router.get("/login")
async def login_page(request: Request):
    """Страница логина."""
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def login(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")

    if not username or not password:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": _(Message.input_login_and_password)},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    request.app.state.logger.error(f"Аутентификация с параметрами {username}, {request.app.state.ldap_uri}")
    user = await authenticate_from_sources(
        username=username,
        password=password,
        user_db=request.app.state.user_db,
        ldap_uri=request.app.state.ldap_uri,
    )

    if not user:
        request.app.state.logger.error(f"Неверные учётные данные для {username}")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": _(Message.invalid_password_or_login)},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    request.session["user"] = user

    oauth_params = request.session.pop("oauth_params", {})
    if oauth_params:
        redirect_url = f"/authorize?client_id={oauth_params['client_id']}&redirect_uri={oauth_params['redirect_uri']}&response_type=code&scope={oauth_params['scope']}"
        if oauth_params.get('state'):
            redirect_url += f"&state={oauth_params['state']}"
        if oauth_params.get("nonce"):
            redirect_url += f"&nonce={oauth_params['nonce']}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    next_url = request.session.pop("next_url", "/")
    return RedirectResponse(url=next_url, status_code=status.HTTP_302_FOUND)



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
