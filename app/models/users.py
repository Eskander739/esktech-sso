from pydantic import BaseModel

from config import settings
from constants import AccessTokenFormat


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: str | None = None
    is_active: bool = True
    token_type: AccessTokenFormat = settings.ACCESS_TOKEN_FORMAT


class UserUpdate(BaseModel):
    email: str | None = None
    password: str | None = None
    full_name: str | None = None
    is_active: bool | None = None

class UserUpdateProfile(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None
    password: str | None = None

class UserChangePassword(BaseModel):
    old_password: str
    new_password: str
