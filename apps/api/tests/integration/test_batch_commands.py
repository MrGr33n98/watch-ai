from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TypeVar
from uuid import uuid4

import pytest

from app.application.batches import BatchSessionService
from app.domain.sessions.batches import BatchResultStatus, NoActiveBatch, SenderBatch
from app.domain.sessions.models import SessionStatus

T = TypeVar("T")


@dataclass
class InMemoryBatchRepository:
    active: dict[str, SenderBatch] = field(default_factory=dict)
    history: list[SenderBatch] = field(default_factory=list)

    def transact(
        self,
        sender_hmac: str,
        operation: Callable[[SenderBatch | None], tuple[SenderBatch | None, T]],
    ) -> T:
        current, result = operation(self.active.get(sender_hmac))
        if current is None:
            self.active.pop(sender_hmac, None)
        else:
            self.active[sender_hmac] = current
        return result


def test_start_orders_questions_and_finalizes_incomplete_batch() -> None:
    repository = InMemoryBatchRepository()
    service = BatchSessionService(repository, expiry=timedelta(minutes=30))
    sender_hmac = "sender-hash"
    owner_id = uuid4()
    now = datetime(2026, 11, 23, 12, tzinfo=UTC)

    started = service.start(sender_hmac, owner_id, expected_count=4, now=now)
    first = service.add_image(sender_hmac, "sha-q1", now=now + timedelta(seconds=1))
    second = service.add_image(sender_hmac, "sha-q2", now=now + timedelta(seconds=2))
    finalized = service.finish(sender_hmac, now=now + timedelta(seconds=3))

    assert started.status is BatchResultStatus.STARTED
    assert (first.ordinal, second.ordinal) == (1, 2)
    assert finalized.session_id == started.session_id
    assert finalized.received_count == 2
    assert finalized.session_status is SessionStatus.QUEUED
    assert sender_hmac not in repository.active


def test_duplicate_start_keeps_current_session_and_configured_count() -> None:
    service = BatchSessionService(InMemoryBatchRepository())
    sender_hmac = "sender-hash"
    owner_id = uuid4()
    now = datetime(2026, 11, 23, 12, tzinfo=UTC)

    first = service.start(sender_hmac, owner_id, expected_count=3, now=now)
    duplicate = service.start(
        sender_hmac,
        owner_id,
        expected_count=4,
        now=now + timedelta(seconds=1),
    )

    assert duplicate.status is BatchResultStatus.ALREADY_ACTIVE
    assert duplicate.session_id == first.session_id
    assert duplicate.expected_count == 3


def test_empty_batch_cannot_be_finalized() -> None:
    repository = InMemoryBatchRepository()
    service = BatchSessionService(repository)
    sender_hmac = "sender-hash"
    service.start(sender_hmac, uuid4())

    with pytest.raises(NoActiveBatch):
        service.finish(sender_hmac)

    assert sender_hmac in repository.active


def test_expired_batch_is_marked_and_cannot_accept_a_late_image() -> None:
    repository = InMemoryBatchRepository()
    service = BatchSessionService(repository, expiry=timedelta(minutes=5))
    now = datetime(2026, 11, 23, 12, tzinfo=UTC)
    started = service.start("sender-hash", uuid4(), now=now)

    expired = service.add_image("sender-hash", "sha-late", now=now + timedelta(minutes=6))

    assert "sender-hash" not in repository.active
    assert started.session_id is not None
    assert expired.status is BatchResultStatus.EXPIRED
    assert expired.session_status is SessionStatus.EXPIRED


def test_expected_count_queues_batch_and_rejects_fifth_question() -> None:
    repository = InMemoryBatchRepository()
    service = BatchSessionService(repository)
    now = datetime(2026, 11, 23, 12, tzinfo=UTC)
    started = service.start("sender-hash", uuid4(), expected_count=4, now=now)

    results = [
        service.add_image("sender-hash", f"sha-q{ordinal}", now=now + timedelta(seconds=ordinal))
        for ordinal in range(1, 5)
    ]

    assert [result.ordinal for result in results] == [1, 2, 3, 4]
    assert results[-1].session_status is SessionStatus.QUEUED
    assert started.session_id == results[-1].session_id
    with pytest.raises(NoActiveBatch):
        service.add_image("sender-hash", "sha-q5", now=now + timedelta(seconds=5))
