from fastapi import Request
from utils.password_validator import verify_password


async def authenticate_user(request: Request, username: str, password: str):
    """Аутентификация пользователя через БД."""
    user_db = request.app.state.user_db
    user = await user_db.get_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user
