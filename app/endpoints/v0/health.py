"""Healthchecks для мониторинга."""
import json

from sqlalchemy import text
from starlette.responses import JSONResponse, Response
from urllib3.exceptions import MaxRetryError, NewConnectionError
from requests.exceptions import ConnectionError
from constants import ApiVersion
from fastapi import APIRouter, HTTPException, Request, status
import requests
from models.general import SSOReadyStatus, ServiceStatus
from models.msg import Message
from services.localization import _
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

router = APIRouter(prefix=f"{ApiVersion.V0}/health", tags=["health"])


@router.get("/live")
async def liveness():
    return {"status": "live"}


@router.get("/", response_model=SSOReadyStatus)
async def readiness(request: Request):
    try:
        sso_ready_status = SSOReadyStatus()
        connected_services = []

        try:
            async with request.app.state.db_pool.get_connection() as session:
                await session.execute(text("SELECT 1"))
            sso_ready_status.postgresql = True
        except Exception as err:
            connected_services.append(ServiceStatus(
                name="PostgreSQL",
                status=False,
                error=str(err)
            ))


        try:
            redis_client = request.app.state.redis_service
            sso_ready_status.redis = await redis_client.check_connection(True)
        except Exception as err:
            sso_ready_status.redis = False
            connected_services.append(ServiceStatus(
                name="Redis",
                status=False,
                error="Redis service is unavailable" if not str(err) else str(err)
            ))

        oauth_client_db = request.app.state.oauth_client_db
        clients = await oauth_client_db.get_all_clients()

        for client in clients:
            start_time = datetime.now()
            try:
                response = requests.get(
                    client.redirect_uris,
                    timeout=5,
                    verify=False  # Для самоподписанных сертификатов
                )
                response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

                connected_services.append(ServiceStatus(
                    name=client.application_name,
                    status=response.status_code == status.HTTP_200_OK,
                    url=client.redirect_uris,
                    response_time_ms=response_time_ms,
                    status_code=response.status_code,
                    last_check=datetime.now()
                ))
            except (ConnectionError, MaxRetryError, NewConnectionError) as e:
                connected_services.append(ServiceStatus(
                    name=client.application_name,
                    status=False,
                    url=client.redirect_uris,
                    error=str(e),
                    last_check=datetime.now()
                ))

        sso_ready_status.services = connected_services
        sso_ready_status.timestamp = datetime.now()
        sso_ready_status.overall_status = all(
            [sso_ready_status.postgresql, sso_ready_status.redis] +
            [s.status for s in connected_services if s.status is not None]
        )

        response_data = sso_ready_status.model_dump(exclude_none=True)
        pretty_json = json.dumps(response_data, indent=4, default=str, ensure_ascii=False)

        return Response(
            content=pretty_json,
            media_type="application/json",
            status_code=status.HTTP_200_OK
        )
    except SQLAlchemyError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{_(Message.internal_error)}: {err!s}"
        )