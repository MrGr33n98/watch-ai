"""Privacy-conscious inbound-message and outbox records."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID, uuid4


class InboundMessageState(StrEnum):
    RECEIVED = "received"
    QUEUED = "queued"
    PROCESSING = "processing"
    PROCESSED = "processed"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class InboundMessage:
    id: UUID = field(default_factory=uuid4)
    provider: str = "waha"
    provider_message_id: str = ""
    sender_hmac: str = ""
    provider_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    session_id: UUID | None = None
    question_ordinal: int | None = None
    media_sha: str | None = None
    state: InboundMessageState = InboundMessageState.RECEIVED

    def __post_init__(self) -> None:
        provider = self.provider.strip().lower()
        if not provider:
            raise ValueError("Inbound provider must not be empty")
        if not self.provider_message_id.strip():
            raise ValueError("Provider message ID must not be empty")
        if not self.sender_hmac.strip():
            raise ValueError("Sender HMAC must not be empty")
        if self.provider_timestamp.utcoffset() is None or self.received_at.utcoffset() is None:
            raise ValueError("Inbound message timestamps must be timezone-aware")
        if self.media_sha is not None and not self.media_sha.strip():
            raise ValueError("Media SHA must be null or non-empty")
        if self.question_ordinal is not None and (
            isinstance(self.question_ordinal, bool)
            or not 1 <= self.question_ordinal <= 4
        ):
            raise ValueError("Inbound question ordinal must be between 1 and 4")
        if provider != self.provider:
            object.__setattr__(self, "provider", provider)


@dataclass(frozen=True, slots=True)
class OutboxEvent:
    id: UUID
    aggregate_type: str
    aggregate_id: UUID
    event_type: str
    payload: Mapping[str, str]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    published_at: datetime | None = None
    attempt_count: int = 0

    def __post_init__(self) -> None:
        if not self.aggregate_type.strip() or not self.event_type.strip():
            raise ValueError("Outbox aggregate and event type must not be empty")
        if self.created_at.utcoffset() is None:
            raise ValueError("Outbox timestamps must be timezone-aware")
        if self.published_at is not None and self.published_at.utcoffset() is None:
            raise ValueError("Outbox timestamps must be timezone-aware")
        if isinstance(self.attempt_count, bool) or self.attempt_count < 0:
            raise ValueError("Outbox attempt count must be non-negative")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))

    @classmethod
    def for_inbound_message(cls, message: InboundMessage) -> OutboxEvent:
        payload = {"message_id": str(message.id)}
        if message.session_id is not None:
            payload["session_id"] = str(message.session_id)
        return cls(
            id=uuid4(),
            aggregate_type="inbound_message",
            aggregate_id=message.id,
            event_type="inbound_message.accepted",
            payload=payload,
        )


def order_messages_by_source_time(
    messages: Iterable[InboundMessage],
) -> tuple[InboundMessage, ...]:
    """Recover provider message order when webhook delivery is out of order."""
    return tuple(
        sorted(
            messages,
            key=lambda message: (
                message.provider_timestamp,
                message.provider,
                message.provider_message_id,
            ),
        )
    )
