"""Pairing and device-token lifecycle endpoints for the watch client."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator

from app.adapters.db.delivery import SqlAlchemyDeliveryRepository
from app.adapters.http.auth import WatchPrincipal, require_watch_principal
from app.adapters.http.database import DatabaseSession
from app.adapters.http.pairing_rate_limit import PairingRateLimiter
from app.application.pairing import PairingService
from app.domain.delivery.models import PairingCodeRejected

router = APIRouter(tags=["watch-device"])
_BEARER_SCHEME = "Bearer"


class PairingRequest(BaseModel):
    pairing_code: str = Field(min_length=6, max_length=12)
    device_name: str = Field(min_length=1, max_length=120)

    @field_validator("device_name")
    @classmethod
    def normalize_device_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Device name must not be blank")
        return normalized


class PairingResponse(BaseModel):
    device_id: UUID
    access_token: str
    token_type: str = _BEARER_SCHEME
    scope: str
    expires_at: datetime


@router.post(
    "/v1/device-pairings",
    response_model=PairingResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="pairWatch",
    responses={
        401: {"description": "Invalid or expired pairing code"},
        429: {"description": "Pairing attempt rate limit exceeded"},
    },
)
def pair_watch(
    request: PairingRequest,
    database: DatabaseSession,
    http_request: Request,
) -> PairingResponse:
    limiter: PairingRateLimiter = http_request.app.state.pairing_rate_limiter
    client_key = http_request.client.host if http_request.client is not None else "unknown"
    if not limiter.allow(client_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many pairing attempts",
            headers={"Retry-After": "60"},
        )
    service = PairingService(SqlAlchemyDeliveryRepository(database))
    try:
        credential = service.pair(request.pairing_code, request.device_name)
    except PairingCodeRejected as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pairing code is invalid, expired, or already used",
        ) from error
    return PairingResponse(
        device_id=credential.device_id,
        access_token=credential.access_token,
        scope=credential.scope,
        expires_at=credential.expires_at,
    )


@router.delete(
    "/v1/devices/me",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="revokeWatchDevice",
    responses={401: {"description": "Unauthorized"}},
)
def revoke_current_device(
    database: DatabaseSession,
    principal: Annotated[WatchPrincipal, Depends(require_watch_principal)],
) -> Response:
    PairingService(SqlAlchemyDeliveryRepository(database)).revoke_device(
        principal.device_id,
        principal.user_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
