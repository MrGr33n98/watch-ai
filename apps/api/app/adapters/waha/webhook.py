"""Authenticated WAHA message webhook boundary."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.adapters.waha.media import WahaMediaError
from app.application.ingestion import IngestionOutcome, IngestionResult
from app.application.ports import AdmittedMediaStorage
from app.domain.ingestion.images import AdmittedJpeg
from app.domain.ingestion.models import InboundMessage
from app.domain.sessions.batches import BatchResult, NoActiveBatch, SenderOwnerMismatch

MAX_WEBHOOK_BODY_BYTES = 1024 * 1024
MAX_PROVIDER_MESSAGE_ID_LENGTH = 512


class InboundMessageIngestor(Protocol):
    def execute(self, message: InboundMessage) -> IngestionResult: ...


class WahaJpegDownloader(Protocol):
    async def download(self, media_url: str, *, declared_mime: str) -> AdmittedJpeg: ...


class WahaBatchCoordinator(Protocol):
    def is_duplicate_message(self, provider_message_id: str) -> bool: ...

    def start(
        self,
        sender_hmac: str,
        owner_id: UUID,
        *,
        expected_count: int = 4,
        now: datetime | None = None,
    ) -> BatchResult: ...

    def require_active(
        self,
        sender_hmac: str,
        owner_id: UUID,
        *,
        now: datetime | None = None,
    ) -> BatchResult: ...

    def add_image(
        self,
        sender_hmac: str,
        media_sha: str,
        *,
        now: datetime | None = None,
        provider_message_id: str | None = None,
        provider_timestamp: datetime | None = None,
    ) -> BatchResult: ...

    def finish(self, sender_hmac: str, *, now: datetime | None = None) -> BatchResult: ...


class WahaTextReplier(Protocol):
    async def send_text(self, *, session: str, chat_id: str, text: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class WahaWebhookSettings:
    enabled: bool = False
    webhook_hmac_secret: str = ""
    sender_hash_secret: str = ""
    allowed_sessions: frozenset[str] = frozenset()
    allowed_senders: frozenset[str] = frozenset()
    media_base_url: str = ""
    media_api_key: str = ""
    media_storage_directory: Path = Path(".watch-ai-private-media")
    sender_owner_ids: Mapping[str, UUID] = field(default_factory=dict)
    default_expected_count: int = 4
    batch_expiry_seconds: int = 3600
    max_body_bytes: int = MAX_WEBHOOK_BODY_BYTES
    send_replies: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.max_body_bytes, bool) or not (
            1 <= self.max_body_bytes <= MAX_WEBHOOK_BODY_BYTES
        ):
            raise ValueError("WAHA webhook body limit must be between 1 byte and 1 MiB")
        object.__setattr__(self, "allowed_sessions", _normalize_set(self.allowed_sessions))
        object.__setattr__(self, "allowed_senders", _normalize_set(self.allowed_senders))
        owner_ids = {
            sender.strip().lower(): owner_id
            for sender, owner_id in self.sender_owner_ids.items()
            if sender.strip()
        }
        if any(not isinstance(owner_id, UUID) for owner_id in owner_ids.values()):
            raise ValueError("WAHA sender owner IDs must be UUID values")
        object.__setattr__(self, "sender_owner_ids", MappingProxyType(owner_ids))
        if isinstance(self.default_expected_count, bool) or not (
            1 <= self.default_expected_count <= 4
        ):
            raise ValueError("WAHA expected question count must be between one and four")
        if isinstance(self.batch_expiry_seconds, bool) or self.batch_expiry_seconds < 1:
            raise ValueError("WAHA batch expiry must be a positive number of seconds")

    @classmethod
    def from_environment(cls) -> WahaWebhookSettings:
        return cls(
            enabled=os.getenv("ENABLE_WAHA_INGEST", "false").strip().lower()
            in {"true", "1", "yes"},
            webhook_hmac_secret=os.getenv("WAHA_WEBHOOK_HMAC_SECRET", ""),
            sender_hash_secret=os.getenv("WAHA_SENDER_HASH_SECRET", ""),
            allowed_sessions=frozenset(_csv_values(os.getenv("WAHA_ALLOWED_SESSIONS", ""))),
            allowed_senders=frozenset(_csv_values(os.getenv("WAHA_ALLOWED_SENDERS", ""))),
            media_base_url=os.getenv("WAHA_BASE_URL", ""),
            media_api_key=os.getenv("WAHA_API_KEY", ""),
            media_storage_directory=Path(
                os.getenv("WATCH_AI_MEDIA_DIR", ".watch-ai-private-media")
            ),
            sender_owner_ids=_parse_sender_owners(os.getenv("WAHA_SENDER_USER_IDS", "")),
            default_expected_count=int(os.getenv("WAHA_DEFAULT_QUESTION_COUNT", "4")),
            batch_expiry_seconds=int(os.getenv("WAHA_BATCH_EXPIRY_SECONDS", "3600")),
            send_replies=os.getenv("WAHA_SEND_REPLIES", "false").strip().lower()
            in {"true", "1", "yes"},
        )

    def owner_id_for_sender(self, sender: str) -> UUID | None:
        return self.sender_owner_ids.get(sender.strip().lower())

    @property
    def ready(self) -> bool:
        return (
            len(self.webhook_hmac_secret.encode()) >= 32
            and len(self.sender_hash_secret.encode()) >= 32
            and bool(self.allowed_sessions)
            and bool(self.allowed_senders)
            and self.allowed_senders.issubset(self.sender_owner_ids)
            and bool(self.media_base_url)
            and bool(self.media_api_key)
        )


router = APIRouter()


@router.post("/waha/webhook", status_code=202, response_model=None)
async def receive_waha_webhook(request: Request) -> dict[str, object] | JSONResponse:
    settings: WahaWebhookSettings = request.app.state.waha_settings
    if not settings.enabled:
        raise HTTPException(status_code=404, detail="Not found")
    if not settings.ready:
        raise HTTPException(status_code=503, detail="WAHA ingestion is not configured")

    body = await _read_bounded_body(request, settings.max_body_bytes)
    _verify_hmac(
        body,
        algorithm=request.headers.get("X-Webhook-Hmac-Algorithm", ""),
        supplied_signature=request.headers.get("X-Webhook-Hmac", ""),
        secret=settings.webhook_hmac_secret,
    )
    event = _parse_json_object(body)

    if event.get("event") != "message":
        return {"status": "ignored", "reason": "unsupported_event"}

    session_name = event.get("session")
    if (
        not isinstance(session_name, str)
        or session_name.strip().lower() not in settings.allowed_sessions
    ):
        raise HTTPException(status_code=403, detail="WAHA session is not allowed")

    payload = event.get("payload")
    if not isinstance(payload, Mapping):
        raise HTTPException(status_code=422, detail="Invalid WAHA message payload")
    from_me = payload.get("fromMe")
    if not isinstance(from_me, bool):
        raise HTTPException(status_code=422, detail="Invalid WAHA sender metadata")
    if from_me:
        return {"status": "ignored", "reason": "from_me"}

    sender = payload.get("from")
    if not isinstance(sender, str) or sender.strip().lower() not in settings.allowed_senders:
        raise HTTPException(status_code=403, detail="WAHA sender is not allowed")

    raw_provider_message_id = payload.get("id")
    if (
        not isinstance(raw_provider_message_id, str)
        or not raw_provider_message_id.strip()
        or len(raw_provider_message_id) > MAX_PROVIDER_MESSAGE_ID_LENGTH
    ):
        raise HTTPException(status_code=422, detail="Invalid WAHA message ID")
    timestamp = _provider_timestamp(payload.get("timestamp"))
    sender_hmac = hmac.new(
        settings.sender_hash_secret.encode(),
        sender.strip().lower().encode(),
        hashlib.sha256,
    ).hexdigest()
    provider_message_id = hmac.new(
        settings.sender_hash_secret.encode(),
        b"waha-message-id:" + raw_provider_message_id.encode(),
        hashlib.sha256,
    ).hexdigest()
    owner_id = settings.owner_id_for_sender(sender)
    batch_service: WahaBatchCoordinator | None = request.app.state.waha_batch_service
    command = _parse_batch_command(payload.get("body"))
    if command is not None:
        if owner_id is None:
            raise HTTPException(status_code=503, detail="WAHA sender owner is not configured")
        if batch_service is None:
            raise HTTPException(status_code=503, detail="Batch processing is unavailable")
        try:
            command_result = (
                batch_service.start(
                    sender_hmac,
                    owner_id,
                    expected_count=command[1] or settings.default_expected_count,
                    now=timestamp,
                )
                if command[0] == "start"
                else batch_service.finish(sender_hmac, now=timestamp)
            )
        except NoActiveBatch as error:
            await _maybe_reply(
                request,
                session=session_name,
                sender=sender,
                text="Nenhum lote ativo com fotos. Envie INICIAR antes das imagens.",
            )
            raise HTTPException(status_code=409, detail=str(error)) from error
        except SenderOwnerMismatch as error:
            raise HTTPException(status_code=403, detail="WAHA sender owner mismatch") from error
        if command_result.status.value == "started":
            reply_text = (
                f"Sessão iniciada (até {command_result.expected_count} fotos JPG). "
                "Envie as imagens ou FINALIZAR."
            )
        elif command_result.status.value == "already_active":
            reply_text = (
                f"Sessão já ativa ({command_result.received_count}/"
                f"{command_result.expected_count}). Envie mais fotos ou FINALIZAR."
            )
        else:
            reply_text = (
                f"Lote fechado ({command_result.received_count} questões). "
                "Processando soluções — abra o Watch AI no relógio."
            )
        await _maybe_reply(request, session=session_name, sender=sender, text=reply_text)
        return {
            "status": command_result.status.value,
            "session_id": str(command_result.session_id),
            "received_count": command_result.received_count,
            "expected_count": command_result.expected_count,
        }

    if payload.get("hasMedia") is not True:
        body_text = str(payload.get("body") or "").strip().lower()
        if body_text in {"ajuda", "help", "como funciona", "oi", "ola", "olá", "status", "info"}:
            help_message = (
                "📚 *Watch AI - Guia de Uso*\n\n"
                "1️⃣ Digite *INICIAR* para abrir um novo lote de exercícios.\n"
                "2️⃣ Envie as *fotos das questões* (1 foto por questão).\n"
                "3️⃣ Digite *FINALIZAR* para processar os cálculos.\n"
                "4️⃣ Abra o Watch AI no seu Galaxy Watch para ver a resolução passo a passo!\n\n"
                "⌚ Código de pareamento permanente: *123456*"
            )
            await _maybe_reply(request, session=session_name, sender=sender, text=help_message)
            return {"status": "replied", "reason": "help_requested"}
        return {"status": "ignored", "reason": "no_media"}
    media = payload.get("media")
    if not isinstance(media, Mapping):
        raise HTTPException(status_code=422, detail="Invalid WAHA media metadata")
    if media.get("mimetype") != "image/jpeg":
        await _maybe_reply(
            request,
            session=session_name,
            sender=sender,
            text="Formato não suportado. Envie cada exercício como imagem ou documento JPG.",
        )
        raise HTTPException(status_code=415, detail="Only JPEG images are accepted")
    media_url = media.get("url")
    if not isinstance(media_url, str) or not media_url.strip() or media.get("error"):
        raise HTTPException(status_code=422, detail="WAHA media is not available")
    if batch_service is None:
        raise HTTPException(status_code=503, detail="Batch processing is unavailable")

    if batch_service.is_duplicate_message(provider_message_id):
        return JSONResponse(
            status_code=200,
            content={"status": "duplicate", "message_id": provider_message_id},
        )

    ingestor: InboundMessageIngestor | None = request.app.state.waha_ingestion
    if ingestor is None:
        raise HTTPException(status_code=503, detail="Message ingestion is unavailable")
    downloader: WahaJpegDownloader | None = request.app.state.waha_media_downloader
    media_store: AdmittedMediaStorage | None = request.app.state.waha_media_store
    if downloader is None or media_store is None:
        raise HTTPException(status_code=503, detail="WAHA media processing is unavailable")
    if owner_id is None:
        raise HTTPException(status_code=503, detail="WAHA sender owner is not configured")
    try:
        batch_service.require_active(sender_hmac, owner_id, now=timestamp)
    except NoActiveBatch as error:
        await _maybe_reply(
            request,
            session=session_name,
            sender=sender,
            text="Nenhuma sessão aberta. Envie INICIAR antes das fotos.",
        )
        raise HTTPException(status_code=409, detail=str(error)) from error
    except SenderOwnerMismatch as error:
        raise HTTPException(status_code=403, detail="WAHA sender owner mismatch") from error
    try:
        admitted = await downloader.download(media_url, declared_mime="image/jpeg")
        await run_in_threadpool(media_store.store, admitted)
    except WahaMediaError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error
    except OSError as error:
        raise HTTPException(
            status_code=503,
            detail="Private media storage is unavailable",
        ) from error
    try:
        batch_result = batch_service.add_image(
            sender_hmac,
            admitted.sha256,
            now=timestamp,
            provider_message_id=provider_message_id,
            provider_timestamp=timestamp,
        )
    except NoActiveBatch as error:
        await _maybe_reply(
            request,
            session=session_name,
            sender=sender,
            text="Lote já concluído. Envie INICIAR para abrir uma nova sessão.",
        )
        raise HTTPException(status_code=409, detail=str(error)) from error
    if batch_result.status.value == "expired":
        await _maybe_reply(
            request,
            session=session_name,
            sender=sender,
            text="Sessão expirada. Envie INICIAR para começar outra.",
        )
        raise HTTPException(status_code=410, detail="WAHA batch expired")
    if batch_result.status.value == "duplicate":
        return JSONResponse(
            status_code=200,
            content={
                "status": "duplicate",
                "message_id": str(batch_result.inbound_message_id or provider_message_id),
            },
        )
    result = (
        IngestionResult(
            outcome=IngestionOutcome.ACCEPTED,
            message_id=str(batch_result.inbound_message_id),
        )
        if batch_result.inbound_message_persisted and batch_result.inbound_message_id is not None
        else ingestor.execute(
            InboundMessage(
                provider="waha",
                provider_message_id=provider_message_id,
                sender_hmac=sender_hmac,
                provider_timestamp=timestamp,
                session_id=batch_result.session_id,
                media_sha=admitted.sha256,
            )
        )
    )
    if result.outcome is IngestionOutcome.DUPLICATE:
        return JSONResponse(
            status_code=200,
            content={"status": "duplicate", "message_id": result.message_id},
        )
    embedded_worker = getattr(request.app.state, "embedded_worker", None)
    if embedded_worker is not None:
        embedded_worker.wake()
    if batch_result.status.value == "finalized":
        reply_text = (
            f"Lote fechado ({batch_result.received_count}/{batch_result.expected_count}). "
            "Processando soluções — abra o Watch AI no relógio."
        )
    else:
        reply_text = (
            f"Questão {batch_result.received_count}/{batch_result.expected_count} recebida."
        )
    await _maybe_reply(request, session=session_name, sender=sender, text=reply_text)
    return {
        "status": "accepted",
        "message_id": result.message_id,
        "session_id": str(batch_result.session_id),
        "ordinal": batch_result.ordinal or 0,
    }


async def _maybe_reply(
    request: Request,
    *,
    session: str,
    sender: str,
    text: str,
) -> None:
    settings: WahaWebhookSettings = request.app.state.waha_settings
    if not settings.send_replies:
        return
    reply_client: WahaTextReplier | None = getattr(request.app.state, "waha_reply_client", None)
    if reply_client is None:
        return
    await reply_client.send_text(session=session, chat_id=sender, text=text)


async def _read_bounded_body(request: Request, maximum_bytes: int) -> bytes:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_size = int(content_length)
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Invalid Content-Length") from error
        if declared_size < 0 or declared_size > maximum_bytes:
            raise HTTPException(status_code=413, detail="WAHA webhook body exceeds the limit")

    chunks = bytearray()
    async for chunk in request.stream():
        if len(chunks) + len(chunk) > maximum_bytes:
            raise HTTPException(status_code=413, detail="WAHA webhook body exceeds the limit")
        chunks.extend(chunk)
    if not chunks:
        raise HTTPException(status_code=400, detail="WAHA webhook body is empty")
    return bytes(chunks)


def _verify_hmac(body: bytes, *, algorithm: str, supplied_signature: str, secret: str) -> None:
    if algorithm.strip().lower() != "sha512" or not supplied_signature:
        raise HTTPException(status_code=401, detail="Invalid WAHA webhook signature")
    expected_signature = hmac.new(secret.encode(), body, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(expected_signature, supplied_signature.strip().lower()):
        raise HTTPException(status_code=401, detail="Invalid WAHA webhook signature")


def _parse_json_object(body: bytes) -> Mapping[str, object]:
    try:
        event = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=422, detail="Invalid JSON payload") from error
    if not isinstance(event, Mapping):
        raise HTTPException(status_code=422, detail="Invalid WAHA event")
    return event


def _provider_timestamp(value: object) -> datetime:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HTTPException(status_code=422, detail="Invalid WAHA message timestamp")
    try:
        return datetime.fromtimestamp(value, tz=UTC)
    except (OverflowError, OSError, ValueError) as error:
        raise HTTPException(status_code=422, detail="Invalid WAHA message timestamp") from error


def _normalize_set(values: frozenset[str]) -> frozenset[str]:
    return frozenset(value.strip().lower() for value in values if value.strip())


def _csv_values(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _parse_sender_owners(value: str) -> dict[str, UUID]:
    owners: dict[str, UUID] = {}
    for item in value.split(","):
        sender, separator, raw_owner_id = item.partition("=")
        if not separator or not sender.strip() or not raw_owner_id.strip():
            if item.strip():
                raise ValueError("WAHA_SENDER_USER_IDS entries must use sender=UUID format")
            continue
        normalized_sender = sender.strip().lower()
        if normalized_sender in owners:
            raise ValueError("WAHA sender owner mapping contains duplicate senders")
        owners[normalized_sender] = UUID(raw_owner_id.strip())
    return owners


def _parse_batch_command(value: object) -> tuple[str, int | None] | None:
    if not isinstance(value, str):
        return None
    parts = value.strip().upper().split()
    if not parts:
        return None
    if parts[0] in {"INICIAR", "START", "COMEÇAR", "COMECAR", "RESET", "LIMPAR"}:
        if len(parts) == 1:
            return ("start", None)
        if len(parts) == 2 and parts[1] in {"1", "2", "3", "4"}:
            return ("start", int(parts[1]))
    if parts in [["FINALIZAR"], ["FINISH"], ["FIM"], ["CONCLUIR"]]:
        return ("finish", None)
    return None
