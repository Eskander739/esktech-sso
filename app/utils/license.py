"""Проверка лицензии (Community / Enterprise)."""

# В реальности здесь будет проверка подписи ключа. Упрощённо:
def is_enterprise(license_key: str) -> bool:
    """Возвращает True, если лицензия Enterprise (снимает лимиты)."""
    # Заглушка: если ключ не пустой и равен секретному слову
    return license_key == "ESKTECH-ENTERPRISE-2026"
