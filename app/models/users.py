from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: str | None = None
    is_active: bool = True


class UserUpdate(BaseModel):
    email: str | None = None
    password: str | None = None
    full_name: str | None = None
    is_active: bool | None = None
