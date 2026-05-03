"""Утилиты для проверки лимитов."""
from fastapi import Request


async def count_oauth_clients(request: Request) -> int:
    """Возвращает количество активных OAuth клиентов."""
    return await request.app.state.oauth_client_db.count_active_clients()


async def check_clients_limit(request: Request) -> bool:
    """Проверяет, не превышен ли лимит клиентов (макс. 2 для community)."""
    count = await count_oauth_clients(request)
    return count < 2
