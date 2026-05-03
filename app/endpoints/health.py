"""Healthchecks для мониторинга."""
from fastapi import APIRouter, HTTPException, Request, status
from models.msg import Message
from services.localization import _
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness():
    return {"status": "alive"}


@router.get("/ready")
async def readiness(request: Request):
    try:
        async with request.app.state.db_pool.get_connection() as session:
            await session.execute("SELECT 1")
        return {"status": "ready"}
    except SQLAlchemyError as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{_(Message.internal_error)}: {err!s}")
