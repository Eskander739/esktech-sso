import uuid
from datetime import UTC, datetime

from config import settings
from constants import AccessTokenFormat, UserRole
from db.models.base import Base
from sqlalchemy import UUID, Boolean, Column, DateTime, Integer, String, Enum as SQLAEnum


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    token_type = Column(
        SQLAEnum(AccessTokenFormat,
                 values_callable=lambda x: [e.value for e in x],
                 name="token_type"),
        default=settings.ACCESS_TOKEN_FORMAT,
        nullable=False,
        index=True
    )
    role = Column(
        SQLAEnum(UserRole,
                 values_callable=lambda x: [e.value for e in x],
                 name="user_role"),
        default=UserRole.USER,
        nullable=False,
        index=True
    )
    access_token = Column(String(255), index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # может быть null если источник LDAP
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(UTC))
