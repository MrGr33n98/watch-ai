from __future__ import annotations

from datetime import UTC, datetime
from math import ceil
from threading import Event
from time import perf_counter

from app.adapters.queue.executor import AsyncInterpretationQueue
from app.adapters.queue.fake_vision import FakeVisionProvider
from app.application.ingestion import IngestInboundMessage, IngestionOutcome
from app.application.interpretation import InterpretationProcessor
from app.domain.ingestion.models import InboundMessage, OutboxEvent
from app.domain.interpretation.models import InterpretedExercise


class _MemoryInboundMessages:
    def __init__(self) -> None:
        self._messages: dict[tuple[str, str], InboundMessage] = {}

    def add_if_absent(self, message: InboundMessage) -> tuple[InboundMessage, bool]:
        key = (message.provider, message.provider_message_id)
        existing = self._messages.get(key)
        if existing is not None:
            return existing, False
        self._messages[key] = message
        return message, True


class _MemoryOutbox:
    def __init__(self) -> None:
        self.events: list[OutboxEvent] = []

    def add(self, event: OutboxEvent) -> None:
        self.events.append(event)


class _MemoryUnitOfWork:
    def __init__(self) -> None:
        self.inbound_messages = _MemoryInboundMessages()
        self.outbox = _MemoryOutbox()

    def __call__(self) -> _MemoryUnitOfWork:
        return self

    def __enter__(self) -> _MemoryUnitOfWork:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


class _BlockedFakeVision:
    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()
        self._delegate = FakeVisionProvider()

    def interpret(
        self,
        message: InboundMessage,
        *,
        image_bytes: bytes | None = None,
    ) -> InterpretedExercise:
        self.started.set()
        if not self.release.wait(timeout=3):
            raise TimeoutError("Performance test did not release fake vision")
        return self._delegate.interpret(message, image_bytes=image_bytes)


def test_ingest_p95_latency_stays_below_one_second_while_vision_is_blocked() -> None:
    unit_of_work = _MemoryUnitOfWork()
    vision = _BlockedFakeVision()
    messages = [
        InboundMessage(
            provider_message_id=f"latency-{index}",
            sender_hmac="performance-test-sender",
            provider_timestamp=datetime.now(UTC),
            media_sha="golden-fourier",
        )
        for index in range(24)
    ]
    durations_ms: list[float] = []

    with AsyncInterpretationQueue(InterpretationProcessor(vision)) as queue:
        ingestion = IngestInboundMessage(unit_of_work, job_scheduler=queue)
        for message in messages:
            started = perf_counter()
            result = ingestion.execute(message)
            durations_ms.append((perf_counter() - started) * 1000)
            assert result.outcome is IngestionOutcome.ACCEPTED

        assert vision.started.wait(timeout=1)
        assert not vision.release.is_set()
        p95_index = ceil(len(durations_ms) * 0.95) - 1
        p95_ms = sorted(durations_ms)[p95_index]
        max_ms = max(durations_ms)
        print(f"INGEST_ACCEPTANCE_LATENCY p95_ms={p95_ms:.3f} max_ms={max_ms:.3f}")
        assert p95_ms < 1_000
        assert max_ms < 1_000

        vision.release.set()
        for message in messages:
            assert queue.result(message.id, timeout=1).needs_review is False

    assert len(unit_of_work.outbox.events) == len(messages)
