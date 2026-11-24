"""Use cases for starting, filling, expiring, and closing sender batches."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol, TypeVar
from uuid import UUID

from app.domain.ingestion.models import InboundMessage
from app.domain.sessions.batches import (
    BatchResult,
    BatchResultStatus,
    NoActiveBatch,
    SenderBatch,
    SenderOwnerMismatch,
)
from app.domain.sessions.models import EmptySession, SessionStatus, StudySession

T = TypeVar("T")


class BatchRepository(Protocol):
    def is_message_seen(self, provider: str, provider_message_id: str) -> bool: ...

    def transact(
        self,
        sender_hmac: str,
        operation: Callable[[SenderBatch | None], tuple[SenderBatch | None, T]],
    ) -> T: ...

    def transact_photo(
        self,
        sender_hmac: str,
        message: InboundMessage,
        operation: Callable[[SenderBatch | None], tuple[SenderBatch | None, BatchResult]],
    ) -> BatchResult: ...


class BatchSessionService:
    """Apply batch rules while the repository serializes updates per sender."""

    def __init__(
        self,
        repository: BatchRepository,
        *,
        expiry: timedelta = timedelta(hours=1),
    ) -> None:
        if expiry <= timedelta(0):
            raise ValueError("Batch expiry must be positive")
        self._repository = repository
        self._expiry = expiry

    def is_duplicate_message(self, provider_message_id: str) -> bool:
        return self._repository.is_message_seen("waha", provider_message_id)

    def start(
        self,
        sender_hmac: str,
        owner_id: UUID,
        *,
        expected_count: int = 4,
        now: datetime | None = None,
    ) -> BatchResult:
        current_time = _aware_now(now)
        candidate = StudySession.new(expected_count)

        def operation(current: SenderBatch | None) -> tuple[SenderBatch, BatchResult]:
            if current is not None:
                self._assert_owner(current, owner_id)
                if current.expires_at > current_time:
                    return current, self._result(current, BatchResultStatus.ALREADY_ACTIVE)
                self._expire(current, current_time)

            batch = SenderBatch(
                sender_hmac=sender_hmac,
                owner_id=owner_id,
                session=candidate,
                expires_at=current_time + self._expiry,
            )
            return batch, self._result(batch, BatchResultStatus.STARTED)

        return self._repository.transact(sender_hmac, operation)

    def add_image(
        self,
        sender_hmac: str,
        media_sha: str,
        *,
        now: datetime | None = None,
        provider_message_id: str | None = None,
        provider_timestamp: datetime | None = None,
    ) -> BatchResult:
        current_time = _aware_now(now)

        def operation(current: SenderBatch | None) -> tuple[SenderBatch | None, BatchResult]:
            if current is None:
                raise NoActiveBatch("Send INICIAR before sending exercise images")
            if current.expires_at <= current_time:
                self._expire(current, current_time)
                return None, self._result(current, BatchResultStatus.EXPIRED)

            question = current.session.attach_question(media_sha)
            result_status = (
                BatchResultStatus.FINALIZED
                if current.session.status is SessionStatus.QUEUED
                else BatchResultStatus.IMAGE_ACCEPTED
            )
            next_batch = current if result_status is BatchResultStatus.IMAGE_ACCEPTED else None
            return next_batch, self._result(current, result_status, ordinal=question.ordinal)

        if provider_message_id is None:
            return self._repository.transact(sender_hmac, operation)
        inbound_message = InboundMessage(
            provider="waha",
            provider_message_id=provider_message_id,
            sender_hmac=sender_hmac,
            provider_timestamp=provider_timestamp or current_time,
            received_at=current_time,
            media_sha=media_sha,
        )
        return self._repository.transact_photo(sender_hmac, inbound_message, operation)

    def require_active(
        self,
        sender_hmac: str,
        owner_id: UUID,
        *,
        now: datetime | None = None,
    ) -> BatchResult:
        """Reject media before download unless the sender has a live owned batch."""
        current_time = _aware_now(now)

        def operation(current: SenderBatch | None) -> tuple[SenderBatch | None, BatchResult | None]:
            if current is None:
                return None, None
            self._assert_owner(current, owner_id)
            if current.expires_at <= current_time:
                self._expire(current, current_time)
                return None, self._result(current, BatchResultStatus.EXPIRED)
            return current, self._result(current, BatchResultStatus.ALREADY_ACTIVE)

        result = self._repository.transact(sender_hmac, operation)
        if result is None:
            raise NoActiveBatch("Send INICIAR before sending exercise images")
        if result.status is BatchResultStatus.EXPIRED:
            raise NoActiveBatch("The active batch expired; send INICIAR to open another")
        return result

    def finish(self, sender_hmac: str, *, now: datetime | None = None) -> BatchResult:
        current_time = _aware_now(now)

        def operation(current: SenderBatch | None) -> tuple[SenderBatch | None, BatchResult]:
            if current is None:
                raise NoActiveBatch("There is no active batch to finalize")
            if current.expires_at <= current_time:
                self._expire(current, current_time)
                return None, self._result(current, BatchResultStatus.EXPIRED)
            try:
                current.session.queue()
            except EmptySession as error:
                raise NoActiveBatch("An empty batch cannot be finalized") from error
            return None, self._result(current, BatchResultStatus.FINALIZED)

        return self._repository.transact(sender_hmac, operation)

    @staticmethod
    def _assert_owner(current: SenderBatch, owner_id: UUID) -> None:
        if current.owner_id != owner_id:
            raise SenderOwnerMismatch("Sender is already associated with another owner")

    @staticmethod
    def _expire(batch: SenderBatch, at: datetime) -> None:
        if batch.session.status in {SessionStatus.CREATED, SessionStatus.COLLECTING}:
            batch.session.transition_to(SessionStatus.EXPIRED, at=at)

    @staticmethod
    def _result(
        batch: SenderBatch,
        status: BatchResultStatus,
        *,
        ordinal: int | None = None,
    ) -> BatchResult:
        return BatchResult(
            status=status,
            session_id=batch.session.id,
            expected_count=batch.session.expected_count,
            received_count=batch.session.received_count,
            session_status=batch.session.status,
            ordinal=ordinal,
        )


def _aware_now(value: datetime | None) -> datetime:
    now = value or datetime.now(UTC)
    if now.utcoffset() is None:
        raise ValueError("Batch timestamps must be timezone-aware")
    return now
