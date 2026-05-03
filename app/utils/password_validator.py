"""Проверка паролей (bcrypt)."""
import bcrypt


def hash_password(password: str) -> str:
    """Хеширование пароля."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Сравнение пароля с хешем."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
