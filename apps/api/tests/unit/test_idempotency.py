from datetime import UTC, datetime, timedelta
from typing import Self
from uuid import UUID, uuid4

from app.application.ingestion import IngestInboundMessage, IngestionOutcome
from app.domain.ingestion.models import InboundMessage, order_messages_by_source_time


class MemoryInboundRepository:
    def __init__(self) -> None:
        self.messages: dict[tuple[str, str], InboundMessage] = {}

    def add_if_absent(self, message: InboundMessage) -> tuple[InboundMessage, bool]:
        key = (message.provider, message.provider_message_id)
        existing = self.messages.get(key)
        if existing is not None:
            return existing, False
        self.messages[key] = message
        return message, True


class MemoryOutboxRepository:
    def __init__(self) -> None:
        self.events: list[object] = []

    def add(self, event: object) -> None:
        self.events.append(event)


class MemoryUnitOfWork:
    def __init__(self) -> None:
        self.inbound_messages = MemoryInboundRepository()
        self.outbox = MemoryOutboxRepository()
        self.commit_count = 0
        self.rollback_count = 0

    def __call__(self) -> Self:
        return self

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc_type is not None:
            self.rollback()

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


class RecordingJobScheduler:
    def __init__(self) -> None:
        self.enqueued: list[InboundMessage] = []

    def enqueue(self, message: InboundMessage) -> None:
        self.enqueued.append(message)


def make_message(
    provider_message_id: str,
    provider_timestamp: datetime,
    session_id: UUID,
) -> InboundMessage:
    return InboundMessage(
        provider="waha",
        provider_message_id=provider_message_id,
        sender_hmac="sender-hmac",
        provider_timestamp=provider_timestamp,
        session_id=session_id,
    )


def test_duplicate_provider_event_creates_one_message_and_one_outbox_event() -> None:
    unit_of_work = MemoryUnitOfWork()
    scheduler = RecordingJobScheduler()
    handler = IngestInboundMessage(unit_of_work, job_scheduler=scheduler)
    message = make_message("message-1", datetime.now(UTC), uuid4())

    first = handler.execute(message)
    duplicate = handler.execute(message)

    assert first.outcome is IngestionOutcome.ACCEPTED
    assert duplicate.outcome is IngestionOutcome.DUPLICATE
    assert len(unit_of_work.inbound_messages.messages) == 1
    assert len(unit_of_work.outbox.events) == 1
    assert unit_of_work.commit_count == 1
    assert scheduler.enqueued == [message]


def test_out_of_order_webhooks_sort_by_provider_timestamp() -> None:
    session_id = uuid4()
    first_timestamp = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)
    earlier_message = make_message("message-earlier", first_timestamp, session_id)
    later_message = make_message(
        "message-later", first_timestamp + timedelta(seconds=1), session_id
    )

    ordered = order_messages_by_source_time([later_message, earlier_message])

    assert [message.provider_message_id for message in ordered] == [
        "message-earlier",
        "message-later",
    ]
