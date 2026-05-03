"""Клиент для LDAP/Active Directory."""
import asyncio
from typing import Any

import ldap
from config import settings


async def authenticate_ldap(username: str, password: str) -> dict[str, Any] | None:
    """Аутентификация через LDAP. Возвращает словарь с информацией о пользователе или None."""
    if not settings.LDAP_URI:
        return None

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync_ldap_auth, username, password)


def _sync_ldap_auth(username: str, password: str) -> dict[str, Any] | None:
    conn = None
    try:
        conn = ldap.initialize(settings.LDAP_URI)
        conn.set_option(ldap.OPT_REFERRALS, 0)
        bind_dn = f"{settings.LDAP_USER_ATTR}={username},{settings.LDAP_BASE_DN}"
        conn.simple_bind_s(bind_dn, password)
        search_filter = f"({settings.LDAP_USER_ATTR}={username})"
        result = conn.search_s(
            settings.LDAP_BASE_DN,
            ldap.SCOPE_SUBTREE,
            search_filter,
            ["mail", "displayName", "cn"]
        )
        if result:
            _, attrs = result[0]
            email = attrs.get("mail", [b""])[0].decode()
            full_name = attrs.get("displayName", [b""])[0].decode() or attrs.get("cn", [b""])[0].decode()
            return {
                "username": username,
                "email": email,
                "full_name": full_name,
                "source": "ldap",
            }
        return {"username": username, "source": "ldap"}
    except ldap.INVALID_CREDENTIALS:
        return None
    except (ldap.LDAPError, ConnectionError, TimeoutError) as e:
        print(f"LDAP connection error: {e}")  # или логирование
        return None
    finally:
        if conn:
            conn.unbind()
