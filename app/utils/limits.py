"""Проверка лимитов Community версии."""
from config import settings
from db.crud import count_oauth_clients
from utils.license import is_enterprise


async def check_clients_limit() -> bool:
    """Проверка, не превышен ли лимит на количество OIDC клиентов."""
    if is_enterprise(settings.LICENSE_KEY):
        return True
    current = await count_oauth_clients()
    return current < settings.COMMUNITY_MAX_CLIENTS


async def check_sources_limit() -> bool:
    if is_enterprise(settings.LICENSE_KEY):
        return True
    return not (settings.LDAP_URI and not is_enterprise(settings.LICENSE_KEY))