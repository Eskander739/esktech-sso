"""Healthchecks для мониторинга."""
from fastapi import APIRouter, Request
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
    except SQLAlchemyError as e:
        return {"status": "not ready", "error": str(e)}, 503