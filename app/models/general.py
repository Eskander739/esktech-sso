from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class ClientCreate(BaseModel):
    name: str
    redirect_uris: str


class ServiceStatus(BaseModel):
    """Статус отдельного сервиса"""
    name: str
    status: bool
    url: Optional[str] = None
    error: Optional[str] = None
    response_time_ms: Optional[int] = None
    status_code: Optional[int] = None
    last_check: datetime = datetime.now()


class SSOReadyStatus(BaseModel):
    """Полный статус готовности SSO"""
    postgresql: bool = False
    redis: bool = False
    services: List[ServiceStatus] = []
    timestamp: datetime = datetime.now()
    overall_status: bool = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }