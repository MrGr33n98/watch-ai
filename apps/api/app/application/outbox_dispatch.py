"""Bounded, privacy-safe retries for durable outbox events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from app.domain.ingestion.models import OutboxEvent


class OutboxDeliveryRepository(Protocol):
    def claim_due(
        self,
        *,
        now: datetime,
        limit: int,
        lease: timedelta,
    ) -> tuple[OutboxEvent, ...]: ...

    def mark_published(self, event_id: UUID, *, at: datetime) -> None: ...

    def record_failure(
        self,
        event_id: UUID,
        *,
        attempt_count: int,
        error_code: str,
        next_attempt_at: datetime | None,
        dead_lettered_at: datetime | None,
    ) -> None: ...


class OutboxEventHandler(Protocol):
    def handle(self, event: OutboxEvent) -> None: ...


class OutboxAuditSink(Protocol):
    def record(
        self,
        *,
        event_type: str,
        outcome: str,
        attempt_count: int,
        error_code: str | None,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 5
    base_delay: timedelta = timedelta(seconds=1)
    max_delay: timedelta = timedelta(minutes=1)
    lease: timedelta = timedelta(minutes=2)
    batch_size: int = 32

    def __post_init__(self) -> None:
        if isinstance(self.max_attempts, bool) or self.max_attempts < 1:
            raise ValueError("Retry max_attempts must be positive")
        if self.base_delay <= timedelta(0) or self.max_delay < self.base_delay:
            raise ValueError("Retry delay bounds are invalid")
        if self.lease <= timedelta(0):
            raise ValueError("Outbox lease must be positive")
        if isinstance(self.batch_size, bool) or self.batch_size < 1:
            raise ValueError("Outbox batch size must be positive")

    def delay_for(self, attempt_count: int) -> timedelta:
        exponent = min(max(attempt_count - 1, 0), 30)
        delay_seconds = min(
            self.base_delay.total_seconds() * (2**exponent),
            self.max_delay.total_seconds(),
        )
        return timedelta(seconds=delay_seconds)


@dataclass(frozen=True, slots=True)
class DispatchSummary:
    claimed: int = 0
    published: int = 0
    retried: int = 0
    dead_lettered: int = 0


class OutboxDispatcher:
    def __init__(
        self,
        repository: OutboxDeliveryRepository,
        handler: OutboxEventHandler,
        audit: OutboxAuditSink,
        *,
        policy: RetryPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._handler = handler
        self._audit = audit
        self._policy = policy or RetryPolicy()

    def dispatch_once(self, *, now: datetime | None = None) -> DispatchSummary:
        current_time = now or datetime.now(UTC)
        if current_time.utcoffset() is None:
            raise ValueError("Outbox dispatch time must be timezone-aware")
        events = self._repository.claim_due(
            now=current_time,
            limit=self._policy.batch_size,
            lease=self._policy.lease,
        )
        published = retried = dead_lettered = 0
        for event in events:
            try:
                self._handler.handle(event)
            except Exception as error:
                code = _safe_error_code(error)
                if event.attempt_count >= self._policy.max_attempts:
                    self._repository.record_failure(
                        event.id,
                        attempt_count=event.attempt_count,
                        error_code=code,
                        next_attempt_at=None,
                        dead_lettered_at=current_time,
                    )
                    self._audit.record(
                        event_type=event.event_type,
                        outcome="dead_lettered",
                        attempt_count=event.attempt_count,
                        error_code=code,
                    )
                    dead_lettered += 1
                else:
                    next_attempt = current_time + self._policy.delay_for(event.attempt_count)
                    self._repository.record_failure(
                        event.id,
                        attempt_count=event.attempt_count,
                        error_code=code,
                        next_attempt_at=next_attempt,
                        dead_lettered_at=None,
                    )
                    self._audit.record(
                        event_type=event.event_type,
                        outcome="retry_scheduled",
                        attempt_count=event.attempt_count,
                        error_code=code,
                    )
                    retried += 1
            else:
                self._repository.mark_published(event.id, at=current_time)
                self._audit.record(
                    event_type=event.event_type,
                    outcome="published",
                    attempt_count=event.attempt_count,
                    error_code=None,
                )
                published += 1
        return DispatchSummary(
            claimed=len(events),
            published=published,
            retried=retried,
            dead_lettered=dead_lettered,
        )


def _safe_error_code(error: Exception) -> str:
    if isinstance(error, TimeoutError):
        return "timeout"
    if isinstance(error, ConnectionError):
        return "connection_error"
    return "processor_error"
