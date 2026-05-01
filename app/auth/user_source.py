"""Абстракция источников пользователей (локальная БД, LDAP, другие)."""
from typing import Any

from auth.ldap_client import authenticate_ldap
from auth.password_validator import verify_password
from db.crud import create_user, get_user_by_id, get_user_by_username
from utils.limits import check_sources_limit


async def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    """
    Аутентификация пользователя по всем доступным источникам.
    Возвращает словарь с данными пользователя (id, username, email, full_name).
    """

    local_user = await get_user_by_username(username)
    if local_user and local_user.get("hashed_password") and verify_password(password, local_user["hashed_password"]):
        return local_user

    if await check_sources_limit():
        ldap_user = await authenticate_ldap(username, password)
        if ldap_user:
            existing = await get_user_by_username(username)
            if existing:
                return existing
            else:
                user_id = await create_user(
                    username=username,
                    email=ldap_user.get("email", f"{username}@ldap.local"),
                    hashed_password=None,
                    full_name=ldap_user.get("full_name", ""),
                )
                return await get_user_by_id(user_id)
    return None