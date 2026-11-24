from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from app.domain.delivery.models import WatchDevice
from app.domain.ingestion.images import AdmittedJpeg
from app.domain.ingestion.models import InboundMessage, OutboxEvent
from app.domain.interpretation.models import InterpretedExercise


class InboundMessageRepository(Protocol):
    def add_if_absent(self, message: InboundMessage) -> tuple[InboundMessage, bool]: ...

    def list_for_session(self, session_id: UUID) -> Sequence[InboundMessage]: ...


class OutboxRepository(Protocol):
    def add(self, event: OutboxEvent) -> None: ...


class UnitOfWork(Protocol):
    inbound_messages: InboundMessageRepository
    outbox: OutboxRepository

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...


class VisionProvider(Protocol):
    def interpret(
        self,
        message: InboundMessage,
        *,
        image_bytes: bytes | None = None,
    ) -> InterpretedExercise: ...


class MessageJobScheduler(Protocol):
    def enqueue(self, message: InboundMessage) -> None: ...


class AdmittedMediaStorage(Protocol):
    def store(self, image: AdmittedJpeg) -> None: ...


class PrivateMediaReader(Protocol):
    def read(self, media_sha: str) -> bytes: ...


class DeliveryRepository(Protocol):
    def add_pairing_code(
        self,
        user_id: UUID,
        code_hash: str,
        created_at: datetime,
        expires_at: datetime,
    ) -> None: ...

    def redeem_pairing_code(
        self,
        code_hash: str,
        device_id: UUID,
        device_name: str,
        token_hash: str,
        created_at: datetime,
        expires_at: datetime,
    ) -> UUID | None: ...

    def find_active_device(self, token_hash: str, now: datetime) -> WatchDevice | None: ...

    def revoke_device(self, device_id: UUID, user_id: UUID, now: datetime) -> bool: ...
