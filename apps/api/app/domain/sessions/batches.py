"""Sender-owned lifecycle for bounded WhatsApp question batches."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.sessions.models import SessionStatus, StudySession


class BatchDomainError(ValueError):
    """Base error for an invalid sender batch operation."""


class NoActiveBatch(BatchDomainError):
    """Raised when an image or close command has no active batch."""


class SenderOwnerMismatch(BatchDomainError):
    """Raised when a sender's active batch is presented with another owner."""


class BatchResultStatus(StrEnum):
    STARTED = "started"
    ALREADY_ACTIVE = "already_active"
    IMAGE_ACCEPTED = "image_accepted"
    FINALIZED = "finalized"
    EXPIRED = "expired"
    DUPLICATE = "duplicate"


@dataclass(slots=True)
class SenderBatch:
    """An active sender binding and its session aggregate."""

    sender_hmac: str
    owner_id: UUID
    session: StudySession
    expires_at: datetime

    def __post_init__(self) -> None:
        if not self.sender_hmac.strip():
            raise ValueError("Sender HMAC must not be empty")
        if self.expires_at.utcoffset() is None:
            raise ValueError("Batch expiration must be timezone-aware")


@dataclass(frozen=True, slots=True)
class BatchResult:
    status: BatchResultStatus
    session_id: UUID | None
    expected_count: int
    received_count: int
    session_status: SessionStatus | None
    ordinal: int | None = None
    inbound_message_persisted: bool = False
    inbound_message_id: UUID | None = None
