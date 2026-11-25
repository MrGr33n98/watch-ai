from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Event

from app.adapters.queue.executor import AsyncInterpretationQueue
from app.adapters.queue.fake_vision import FakeVisionProvider
from app.application.ingestion import IngestInboundMessage, IngestionOutcome
from app.application.interpretation import InterpretationProcessor
from app.domain.ingestion.models import InboundMessage, OutboxEvent


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
        self.events: list[OutboxEvent] = []

    def add(self, event: OutboxEvent) -> None:
        self.events.append(event)


class MemoryUnitOfWork:
    def __init__(self) -> None:
        self.inbound_messages = MemoryInboundRepository()
        self.outbox = MemoryOutboxRepository()
        self.commits = 0

    def __call__(self) -> MemoryUnitOfWork:
        return self

    def __enter__(self) -> MemoryUnitOfWork:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        return None


class GatedVisionProvider:
    def __init__(self, delegate: FakeVisionProvider) -> None:
        self.delegate = delegate
        self.started = Event()
        self.release = Event()

    def interpret(self, message: InboundMessage, *, image_bytes: bytes | None = None):
        self.started.set()
        if not self.release.wait(timeout=3):
            raise TimeoutError("Test did not release the fake provider")
        return self.delegate.interpret(message, image_bytes=image_bytes)


def test_acceptance_returns_before_fake_vision_finishes() -> None:
    unit_of_work = MemoryUnitOfWork()
    fake_vision = FakeVisionProvider()
    gated_vision = GatedVisionProvider(fake_vision)
    message = InboundMessage(
        provider="waha",
        provider_message_id="async-message-1",
        sender_hmac="sender-hmac",
        provider_timestamp=datetime.now(UTC),
        media_sha="golden-fourier",
    )

    with AsyncInterpretationQueue(InterpretationProcessor(gated_vision)) as queue:
        handler = IngestInboundMessage(unit_of_work, job_scheduler=queue)
        with ThreadPoolExecutor(max_workers=1) as request_executor:
            accepted = request_executor.submit(handler.execute, message)
            try:
                assert gated_vision.started.wait(timeout=1)
                result = accepted.result(timeout=0.5)
                returned_before_provider = not gated_vision.release.is_set()
            finally:
                gated_vision.release.set()

        interpretation = queue.result(message.id, timeout=1)

    assert returned_before_provider
    assert result.outcome is IngestionOutcome.ACCEPTED
    assert unit_of_work.commits == 1
    assert len(unit_of_work.outbox.events) == 1
    assert fake_vision.call_count == 1
    assert interpretation.problem_type == "Fourier law"
    assert interpretation.needs_review is False


def test_ambiguous_fake_image_is_flagged_for_review() -> None:
    interpretation = FakeVisionProvider().interpret(
        InboundMessage(
            provider="waha",
            provider_message_id="ambiguous-image",
            sender_hmac="sender-hmac",
            provider_timestamp=datetime.now(UTC),
            media_sha="ambiguous",
        )
    )

    assert interpretation.confidence.value == "low"
    assert interpretation.needs_review is True
