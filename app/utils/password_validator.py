"""Проверка паролей (bcrypt)."""
import re

import bcrypt


def hash_password(password: str) -> str:
    """Хеширование пароля."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Сравнение пароля с хешем."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def validate_password_strength(password: str) -> tuple[bool, str | None]:
    """
    Проверка сложности пароля.

    Правила:
    - Минимум 8 символов
    - Хотя бы одна буква в верхнем регистре
    - Хотя бы одна буква в нижнем регистре
    - Хотя бы одна цифра
    - Хотя бы один специальный символ (опционально)

    Returns:
        (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Пароль должен содержать минимум 8 символов"

    if not re.search(r'[A-Z]', password):
        return False, "Пароль должен содержать хотя бы одну заглавную букву"

    if not re.search(r'[a-z]', password):
        return False, "Пароль должен содержать хотя бы одну строчную букву"

    if not re.search(r'\d', password):
        return False, "Пароль должен содержать хотя бы одну цифру"

    return True, None


def is_password_strong(password: str) -> bool:
    """Упрощённая проверка (только True/False)."""
    valid, _ = validate_password_strength(password)
    return valid