"""Operator/admin endpoints for user provisioning, pairing, remote revocation, and phone upload."""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field

from app.adapters.db.delivery import SqlAlchemyDeliveryRepository
from app.adapters.db.models import (
    InboundMessageRecord,
    OutboxEventRecord,
    QuestionRecord,
    StudySessionRecord,
    UserRecord,
)
from app.adapters.db.retention import SqlAlchemySessionRetentionRepository
from app.adapters.db.session_queries import SqlAlchemySessionQueryRepository
from app.adapters.http.database import DatabaseSession
from app.adapters.http.watch_api import (
    QuestionDetailResponse,
    SessionListResponse,
    SessionSummaryResponse,
    StudySessionResponse,
)
from app.adapters.storage.jpeg import JpegAdmissionError, PillowJpegAdmission
from app.application.pairing import PairingService
from app.application.ports import AdmittedMediaStorage
from app.application.retention import SessionRetentionService
from app.application.session_queries import SessionQueries
from app.domain.ingestion.models import InboundMessage, InboundMessageState, OutboxEvent

router = APIRouter(prefix="/v1/admin", tags=["admin"])
MIN_ADMIN_KEY_BYTES = 32
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


def require_admin_key(request: Request) -> None:
    configured_key: str = getattr(request.app.state, "admin_api_key", "") or ""
    if len(configured_key.encode("utf-8")) < MIN_ADMIN_KEY_BYTES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    supplied = request.headers.get("X-Admin-Key", "")
    if not supplied or not hmac.compare_digest(supplied, configured_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin key")


AdminAccess = Annotated[None, Depends(require_admin_key)]


class CreateUserResponse(BaseModel):
    user_id: UUID


class CreatePairingRequest(BaseModel):
    user_id: UUID
    ttl_minutes: int = Field(default=10, ge=1, le=60)


class CreatePairingResponse(BaseModel):
    pairing_code: str
    expires_at: datetime


class WatchDeviceItem(BaseModel):
    device_id: UUID
    device_name: str
    scope: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    active: bool


class WatchDeviceListResponse(BaseModel):
    items: list[WatchDeviceItem]


class PhoneBatchUploadResponse(BaseModel):
    session_id: UUID
    status: str
    received_count: int
    expected_count: int


class BudgetResponse(BaseModel):
    month: str
    spent_usd: str
    limit_usd: str | None
    remaining_usd: str | None
    exceeded: bool


@router.post("/users", response_model=CreateUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(_admin: AdminAccess, database: DatabaseSession) -> CreateUserResponse:
    user_id = uuid4()
    database.add(UserRecord(id=user_id))
    database.commit()
    return CreateUserResponse(user_id=user_id)


@router.post("/pairings", response_model=CreatePairingResponse, status_code=status.HTTP_201_CREATED)
def create_pairing_code(
    payload: CreatePairingRequest,
    _admin: AdminAccess,
    database: DatabaseSession,
) -> CreatePairingResponse:
    repo = SqlAlchemyDeliveryRepository(database)
    if not repo.user_exists(payload.user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=payload.ttl_minutes)
    code = PairingService(repo).create_pairing_code(
        payload.user_id,
        expires_at=expires_at,
        now=now,
    )
    return CreatePairingResponse(pairing_code=code, expires_at=expires_at)


@router.get("/users/{user_id}/devices", response_model=WatchDeviceListResponse)
def list_user_devices(
    user_id: UUID,
    _admin: AdminAccess,
    database: DatabaseSession,
) -> WatchDeviceListResponse:
    repo = SqlAlchemyDeliveryRepository(database)
    if not repo.user_exists(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    now = datetime.now(UTC)
    items = [
        WatchDeviceItem(
            device_id=device.device_id,
            device_name=device.device_name,
            scope=device.scope,
            created_at=device.created_at,
            expires_at=device.expires_at,
            revoked_at=device.revoked_at,
            active=device.revoked_at is None and device.expires_at > now,
        )
        for device in PairingService(repo).list_devices(user_id)
    ]
    return WatchDeviceListResponse(items=items)


@router.delete("/users/{user_id}/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_user_device(
    user_id: UUID,
    device_id: UUID,
    _admin: AdminAccess,
    database: DatabaseSession,
) -> Response:
    revoked = PairingService(SqlAlchemyDeliveryRepository(database)).revoke_device(
        device_id,
        user_id,
    )
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users/{user_id}/sessions", response_model=SessionListResponse)
def list_user_sessions(
    user_id: UUID,
    _admin: AdminAccess,
    database: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> SessionListResponse:
    queries = SessionQueries(SqlAlchemySessionQueryRepository(database))
    items = [
        SessionSummaryResponse.model_validate(item)
        for item in queries.list_sessions(user_id, limit)
    ]
    return SessionListResponse(items=items, next_cursor=None)


@router.get("/users/{user_id}/sessions/{session_id}", response_model=StudySessionResponse)
def get_user_session(
    user_id: UUID,
    session_id: UUID,
    _admin: AdminAccess,
    database: DatabaseSession,
) -> StudySessionResponse:
    result = SessionQueries(SqlAlchemySessionQueryRepository(database)).get_session(
        user_id,
        session_id,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return StudySessionResponse.model_validate(result)


@router.get(
    "/users/{user_id}/sessions/{session_id}/questions/{ordinal}",
    response_model=QuestionDetailResponse,
)
def get_user_question(
    user_id: UUID,
    session_id: UUID,
    ordinal: Annotated[int, Path(ge=1, le=4)],
    _admin: AdminAccess,
    database: DatabaseSession,
) -> QuestionDetailResponse:
    result = SessionQueries(SqlAlchemySessionQueryRepository(database)).get_question(
        user_id,
        session_id,
        ordinal,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return QuestionDetailResponse.model_validate(result)


@router.delete("/users/{user_id}/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_session(
    user_id: UUID,
    session_id: UUID,
    request: Request,
    _admin: AdminAccess,
    database: DatabaseSession,
) -> Response:
    retention = SessionRetentionService(
        SqlAlchemySessionRetentionRepository(database),
        request.app.state.waha_media_store,
        request.app.state.session_retention_policy,
    )
    if not retention.delete_session(user_id, session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/users/{user_id}/batches/upload",
    response_model=PhoneBatchUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_phone_batch(
    user_id: UUID,
    request: Request,
    _admin: AdminAccess,
    database: DatabaseSession,
    files: Annotated[list[UploadFile], File(...)],
) -> PhoneBatchUploadResponse:
    if not SqlAlchemyDeliveryRepository(database).user_exists(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not (1 <= len(files) <= 4):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie entre 1 e 4 imagens JPG.",
        )

    media_store: AdmittedMediaStorage | None = getattr(request.app.state, "waha_media_store", None)
    if media_store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Private media storage is unavailable",
        )

    admission = PillowJpegAdmission(max_bytes=MAX_UPLOAD_BYTES)
    admitted_images = []
    for upload in files:
        declared_mime = (upload.content_type or "image/jpeg").strip().lower()
        if declared_mime not in {"image/jpeg", "image/jpg"}:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Only image/jpeg files are accepted",
            )
        raw_bytes = await upload.read(MAX_UPLOAD_BYTES + 1)
        if len(raw_bytes) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Image exceeds the 8 MiB size limit",
            )
        try:
            admitted = admission.admit(raw_bytes, "image/jpeg")
        except JpegAdmissionError as error:
            raise HTTPException(status_code=error.status_code, detail=str(error)) from error
        media_store.store(admitted)
        admitted_images.append(admitted)

    now = datetime.now(UTC)
    session_id = uuid4()
    sender_hmac = hashlib.sha256(f"phone:{user_id}".encode()).hexdigest()
    count = len(admitted_images)

    database.add(
        StudySessionRecord(
            id=session_id,
            user_id=user_id,
            status="queued",
            expected_count=count,
            received_count=count,
            created_at=now,
        )
    )
    database.flush()
    for ordinal, admitted in enumerate(admitted_images, start=1):
        database.add(
            QuestionRecord(
                id=uuid4(),
                session_id=session_id,
                ordinal=ordinal,
                status="uploaded",
                media_sha=admitted.sha256,
                created_at=now,
                updated_at=now,
            )
        )
        message = InboundMessage(
            provider="phone_web",
            provider_message_id=f"phone-{session_id}-{ordinal}",
            sender_hmac=sender_hmac,
            provider_timestamp=now + timedelta(milliseconds=ordinal),
            received_at=now,
            session_id=session_id,
            question_ordinal=ordinal,
            media_sha=admitted.sha256,
            state=InboundMessageState.QUEUED,
        )
        database.add(
            InboundMessageRecord(
                id=message.id,
                provider=message.provider,
                provider_message_id=message.provider_message_id,
                sender_hmac=message.sender_hmac,
                media_sha=message.media_sha,
                session_id=session_id,
                question_ordinal=ordinal,
                state=message.state.value,
                provider_timestamp=message.provider_timestamp,
                received_at=message.received_at,
            )
        )
        event = OutboxEvent.for_inbound_message(message)
        database.add(
            OutboxEventRecord(
                id=event.id,
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                event_type=event.event_type,
                payload=dict(event.payload),
                created_at=event.created_at,
                next_attempt_at=event.created_at,
                attempt_count=0,
            )
        )
    database.commit()

    embedded_worker = getattr(request.app.state, "embedded_worker", None)
    if embedded_worker is not None:
        embedded_worker.wake()

    return PhoneBatchUploadResponse(
        session_id=session_id,
        status="queued",
        received_count=count,
        expected_count=count,
    )


@router.get("/budget", response_model=BudgetResponse)
def get_budget(request: Request, _admin: AdminAccess) -> BudgetResponse:
    snapshot = request.app.state.model_budget.snapshot()
    return BudgetResponse(
        month=snapshot.month,
        spent_usd=str(snapshot.spent_usd),
        limit_usd=str(snapshot.limit_usd) if snapshot.limit_usd is not None else None,
        remaining_usd=(
            str(snapshot.remaining_usd) if snapshot.remaining_usd is not None else None
        ),
        exceeded=snapshot.exceeded,
    )
