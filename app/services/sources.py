"""Аутентификация из нескольких источников."""

from db.users import UserDB
from utils.ldap_client import authenticate_ldap
from utils.password_validator import verify_password


async def authenticate_from_sources(
        username: str,
        password: str,
        user_db: UserDB,
        ldap_uri: str | None = None,
) -> dict | None:
    """
    Аутентификация пользователя по всем доступным источникам.
    Возвращает пользователя из БД (создаёт при необходимости).
    """

    user = await user_db.get_by_username(username)
    if user and user.get("hashed_password") and verify_password(password, user["hashed_password"]):
        return user

    elif ldap_uri:
        ldap_info = await authenticate_ldap(username, password)
        if ldap_info:

            existing = await user_db.get_by_username(username)
            if existing:
                user_id = existing["id"]
                if ldap_info.get("email"):
                    await user_db.update_email(user_id, ldap_info["email"])
                if ldap_info.get("full_name"):
                    await user_db.update_full_name(user_id, ldap_info["full_name"])
            else:
                user_id = await user_db.create(
                    username=username,
                    email=ldap_info.get("email", f"{username}@ldap.local"),
                    hashed_password=None,
                    full_name=ldap_info.get("full_name", username),
                    is_active=True,
                )
            return await user_db.get_by_id(user_id)

    return None