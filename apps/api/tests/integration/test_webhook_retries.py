from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.db.base import Base
from app.adapters.db.models import OutboxEventRecord
from app.adapters.db.outbox_delivery import SqlAlchemyOutboxDeliveryRepository
from app.application.outbox_dispatch import (
    OutboxDispatcher,
    RetryPolicy,
)
from app.domain.ingestion.models import InboundMessage, OutboxEvent


@dataclass
class FakeOutboxRepository:
    events: dict[UUID, OutboxEvent]
    next_attempt_at: dict[UUID, datetime] = field(default_factory=dict)
    leases: dict[UUID, datetime] = field(default_factory=dict)
    dead_lettered: set[UUID] = field(default_factory=set)
    published: set[UUID] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)

    def claim_due(
        self,
        *,
        now: datetime,
        limit: int,
        lease: timedelta,
    ) -> tuple[OutboxEvent, ...]:
        claimed: list[OutboxEvent] = []
        for event_id, event in self.events.items():
            if event_id in self.published or event_id in self.dead_lettered:
                continue
            if self.next_attempt_at.get(event_id, event.created_at) > now:
                continue
            if self.leases.get(event_id, now) > now:
                continue
            updated = replace(event, attempt_count=event.attempt_count + 1)
            self.events[event_id] = updated
            self.leases[event_id] = now + lease
            claimed.append(updated)
            if len(claimed) == limit:
                break
        return tuple(claimed)

    def mark_published(self, event_id: UUID, *, at: datetime) -> None:
        del at
        self.published.add(event_id)
        self.leases.pop(event_id, None)

    def record_failure(
        self,
        event_id: UUID,
        *,
        attempt_count: int,
        error_code: str,
        next_attempt_at: datetime | None,
        dead_lettered_at: datetime | None,
    ) -> None:
        self.errors.append(error_code)
        self.leases.pop(event_id, None)
        if dead_lettered_at is not None:
            self.dead_lettered.add(event_id)
        elif next_attempt_at is not None:
            self.next_attempt_at[event_id] = next_attempt_at
        self.events[event_id] = replace(
            self.events[event_id],
            attempt_count=attempt_count,
        )


class FlakyHandler:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    def handle(self, event: OutboxEvent) -> None:
        del event
        self.calls += 1
        if self.calls <= self.failures:
            raise TimeoutError("private message data must never enter audit output")


class RecordingAudit:
    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []

    def record(self, **fields: object) -> None:
        self.records.append(fields)


def _event() -> OutboxEvent:
    message = InboundMessage(
        provider_message_id="opaque-provider-id",
        sender_hmac="a" * 64,
        media_sha="b" * 64,
        provider_timestamp=datetime(2026, 11, 23, 12, tzinfo=UTC),
    )
    event = OutboxEvent.for_inbound_message(message)
    return replace(event, created_at=datetime(2026, 11, 23, 11, tzinfo=UTC))


def test_transient_failure_retries_then_succeeds_with_sanitized_audit() -> None:
    event = _event()
    repository = FakeOutboxRepository({event.id: event})
    handler = FlakyHandler(failures=1)
    audit = RecordingAudit()
    dispatcher = OutboxDispatcher(
        repository,
        handler,
        audit,
        policy=RetryPolicy(max_attempts=3, base_delay=timedelta(seconds=2)),
    )
    now = datetime(2026, 11, 23, 12, tzinfo=UTC)

    first = dispatcher.dispatch_once(now=now)
    second = dispatcher.dispatch_once(now=now + timedelta(seconds=2))

    assert first.retried == 1
    assert second.published == 1
    assert handler.calls == 2
    assert repository.errors == ["timeout"]
    assert repository.published == {event.id}
    assert "private message data" not in repr(audit.records)
    assert audit.records[0]["outcome"] == "retry_scheduled"


def test_exhausted_retries_move_event_to_dead_letter_without_exception_text() -> None:
    event = _event()
    repository = FakeOutboxRepository({event.id: event})
    handler = FlakyHandler(failures=10)
    audit = RecordingAudit()
    dispatcher = OutboxDispatcher(
        repository,
        handler,
        audit,
        policy=RetryPolicy(max_attempts=2, base_delay=timedelta(seconds=1)),
    )
    now = datetime(2026, 11, 23, 12, tzinfo=UTC)

    first = dispatcher.dispatch_once(now=now)
    second = dispatcher.dispatch_once(now=now + timedelta(seconds=1))

    assert first.retried == 1
    assert second.dead_lettered == 1
    assert repository.dead_lettered == {event.id}
    assert repository.errors == ["timeout", "timeout"]
    assert "opaque-provider-id" not in repr(audit.records)
    assert "private message data" not in repr(audit.records)


def test_sql_outbox_lease_recovers_after_worker_crash() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[OutboxEventRecord.__table__])
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    event = _event()
    with session_factory.begin() as session:
        session.add(
            OutboxEventRecord(
                id=event.id,
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                event_type=event.event_type,
                payload=dict(event.payload),
                created_at=event.created_at,
                next_attempt_at=event.created_at,
            )
        )
    repository = SqlAlchemyOutboxDeliveryRepository(session_factory)
    now = datetime(2026, 11, 23, 12, tzinfo=UTC)

    first_claim = repository.claim_due(
        now=now,
        limit=1,
        lease=timedelta(seconds=5),
    )
    blocked_by_lease = repository.claim_due(
        now=now + timedelta(seconds=4),
        limit=1,
        lease=timedelta(seconds=5),
    )
    recovered_claim = repository.claim_due(
        now=now + timedelta(seconds=5),
        limit=1,
        lease=timedelta(seconds=5),
    )

    assert [item.attempt_count for item in first_claim] == [1]
    assert blocked_by_lease == ()
    assert [item.attempt_count for item in recovered_claim] == [2]
    repository.mark_published(event.id, at=now + timedelta(seconds=5))
    assert repository.claim_due(
        now=now + timedelta(seconds=10),
        limit=1,
        lease=timedelta(seconds=5),
    ) == ()
    engine.dispose()
