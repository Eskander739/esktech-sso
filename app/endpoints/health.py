"""Healthchecks для мониторинга."""
from db.database import async_session_maker
from fastapi import APIRouter
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness():
    return {"status": "alive"}


@router.get("/ready")
async def readiness():
    try:
        async with async_session_maker() as session:
            await session.execute("SELECT 1")
        return {"status": "ready"}
    except SQLAlchemyError as e:
        return {"status": "not ready", "error": str(e)}, 503
