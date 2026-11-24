"""SQLAlchemy repository for sender-owned active study batches."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import TypeVar

from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.adapters.db.models import (
    InboundMessageRecord,
    OutboxEventRecord,
    QuestionRecord,
    SenderSessionBindingRecord,
    StudySessionRecord,
)
from app.application.batches import BatchRepository
from app.domain.ingestion.models import InboundMessage, OutboxEvent
from app.domain.sessions.batches import BatchResult, BatchResultStatus, SenderBatch
from app.domain.sessions.models import (
    QuestionItem,
    QuestionOrder,
    QuestionStatus,
    SessionStatus,
    StudySession,
)

T = TypeVar("T")


class SqlAlchemyBatchRepository(BatchRepository):
    """Run each sender mutation under a database row lock and one transaction."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def is_message_seen(self, provider: str, provider_message_id: str) -> bool:
        with self._session_factory() as session:
            return (
                session.scalar(
                    select(InboundMessageRecord.id).where(
                        InboundMessageRecord.provider == provider,
                        InboundMessageRecord.provider_message_id == provider_message_id,
                    )
                )
                is not None
            )

    def transact(
        self,
        sender_hmac: str,
        operation: Callable[[SenderBatch | None], tuple[SenderBatch | None, T]],
    ) -> T:
        with self._session_factory() as session, session.begin():
            self._lock_sender(session, sender_hmac)
            binding = session.scalar(
                select(SenderSessionBindingRecord)
                .where(SenderSessionBindingRecord.sender_hmac == sender_hmac)
                .with_for_update()
            )
            current_record = (
                session.scalar(
                    select(StudySessionRecord)
                    .where(StudySessionRecord.id == binding.session_id)
                    .options(selectinload(StudySessionRecord.questions))
                    .with_for_update()
                )
                if binding is not None
                else None
            )
            current = (
                self._to_domain(binding, current_record)
                if binding is not None and current_record is not None
                else None
            )
            updated, result = operation(current)
            self._persist(session, binding, current_record, current, updated)
            return result

    def transact_photo(
        self,
        sender_hmac: str,
        message: InboundMessage,
        operation: Callable[[SenderBatch | None], tuple[SenderBatch | None, BatchResult]],
    ) -> BatchResult:
        with self._session_factory() as session, session.begin():
            self._lock_sender(session, sender_hmac)
            existing = session.scalar(
                select(InboundMessageRecord)
                .where(
                    InboundMessageRecord.provider == message.provider,
                    InboundMessageRecord.provider_message_id == message.provider_message_id,
                )
                .with_for_update()
            )
            if existing is not None:
                stored_session = (
                    session.get(StudySessionRecord, existing.session_id)
                    if existing.session_id is not None
                    else None
                )
                return BatchResult(
                    status=BatchResultStatus.DUPLICATE,
                    session_id=existing.session_id,
                    expected_count=stored_session.expected_count if stored_session else 0,
                    received_count=stored_session.received_count if stored_session else 0,
                    session_status=(
                        SessionStatus(stored_session.status) if stored_session else None
                    ),
                    ordinal=existing.question_ordinal,
                    inbound_message_persisted=True,
                    inbound_message_id=existing.id,
                )

            binding = session.scalar(
                select(SenderSessionBindingRecord)
                .where(SenderSessionBindingRecord.sender_hmac == sender_hmac)
                .with_for_update()
            )
            current_record = (
                session.scalar(
                    select(StudySessionRecord)
                    .where(StudySessionRecord.id == binding.session_id)
                    .options(selectinload(StudySessionRecord.questions))
                    .with_for_update()
                )
                if binding is not None
                else None
            )
            current = (
                self._to_domain(binding, current_record)
                if binding is not None and current_record is not None
                else None
            )
            updated, result = operation(current)
            self._persist(session, binding, current_record, current, updated)

            if result.status in {
                BatchResultStatus.IMAGE_ACCEPTED,
                BatchResultStatus.FINALIZED,
            }:
                if result.session_id is None or result.ordinal is None:
                    raise RuntimeError("Accepted image must have a session and question ordinal")
                stored_message = replace(
                    message,
                    session_id=result.session_id,
                    question_ordinal=result.ordinal,
                )
                session.add(
                    InboundMessageRecord(
                        id=stored_message.id,
                        provider=stored_message.provider,
                        provider_message_id=stored_message.provider_message_id,
                        sender_hmac=stored_message.sender_hmac,
                        media_sha=stored_message.media_sha,
                        session_id=stored_message.session_id,
                        question_ordinal=stored_message.question_ordinal,
                        state=stored_message.state.value,
                        provider_timestamp=stored_message.provider_timestamp,
                        received_at=stored_message.received_at,
                    )
                )
                event = OutboxEvent.for_inbound_message(stored_message)
                session.add(
                    OutboxEventRecord(
                        id=event.id,
                        aggregate_type=event.aggregate_type,
                        aggregate_id=event.aggregate_id,
                        event_type=event.event_type,
                        payload=dict(event.payload),
                        created_at=event.created_at,
                        next_attempt_at=event.created_at,
                        attempt_count=event.attempt_count,
                    )
                )
                result = replace(
                    result,
                    inbound_message_persisted=True,
                    inbound_message_id=stored_message.id,
                )
            return result

    @staticmethod
    def _lock_sender(session: Session, sender_hmac: str) -> None:
        if session.get_bind().dialect.name != "postgresql":
            return
        raw_key = int.from_bytes(
            hashlib.blake2b(sender_hmac.encode(), digest_size=8).digest(),
            "big",
        )
        lock_key = raw_key - (1 << 64) if raw_key >= (1 << 63) else raw_key
        session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": lock_key},
        )

    @staticmethod
    def _to_domain(
        binding: SenderSessionBindingRecord,
        record: StudySessionRecord,
    ) -> SenderBatch:
        questions: list[QuestionItem] = []
        for question in sorted(record.questions, key=lambda item: item.ordinal):
            if question.media_sha is None:
                raise RuntimeError("Active batch question is missing its admitted media hash")
            questions.append(
                QuestionItem(
                    id=question.id,
                    order=QuestionOrder(question.ordinal),
                    media_sha=question.media_sha,
                    status=QuestionStatus(question.status),
                )
            )
        aggregate = StudySession(
            id=record.id,
            expected_count=record.expected_count,
            status=SessionStatus(record.status),
            created_at=_aware_utc(record.created_at),
            completed_at=(
                _aware_utc(record.completed_at) if record.completed_at is not None else None
            ),
            _questions=questions,
        )
        return SenderBatch(
            sender_hmac=binding.sender_hmac,
            owner_id=record.user_id,
            session=aggregate,
            expires_at=_aware_utc(binding.expires_at),
        )

    @classmethod
    def _persist(
        cls,
        session: Session,
        binding: SenderSessionBindingRecord | None,
        current_record: StudySessionRecord | None,
        current: SenderBatch | None,
        updated: SenderBatch | None,
    ) -> None:
        if current_record is not None and binding is not None and current is not None:
            if updated is None or updated.session.id != current.session.id:
                cls._write_session(session, current, record=current_record)
                session.delete(binding)
                session.flush()
                if updated is None:
                    return
                cls._write_session(session, updated)
                session.add(
                    SenderSessionBindingRecord(
                        sender_hmac=updated.sender_hmac,
                        session_id=updated.session.id,
                        expires_at=updated.expires_at,
                    )
                )
                return
            cls._write_session(session, updated, record=current_record)
            binding.expires_at = updated.expires_at
            return

        if updated is None:
            return
        cls._write_session(session, updated)
        session.add(
            SenderSessionBindingRecord(
                sender_hmac=updated.sender_hmac,
                session_id=updated.session.id,
                expires_at=updated.expires_at,
            )
        )

    @staticmethod
    def _write_session(
        session: Session,
        batch: SenderBatch,
        *,
        record: StudySessionRecord | None = None,
    ) -> None:
        aggregate = batch.session
        if record is None:
            record = StudySessionRecord(
                id=aggregate.id,
                user_id=batch.owner_id,
                status=aggregate.status.value,
                expected_count=aggregate.expected_count,
                received_count=aggregate.received_count,
                created_at=aggregate.created_at,
                completed_at=aggregate.completed_at,
                expires_at=batch.expires_at,
            )
            session.add(record)
            existing_question_ids: set[object] = set()
        else:
            record.status = aggregate.status.value
            record.expected_count = aggregate.expected_count
            record.received_count = aggregate.received_count
            record.completed_at = aggregate.completed_at
            record.expires_at = batch.expires_at
            existing_question_ids = {question.id for question in record.questions}

        for question in aggregate.questions:
            if question.id in existing_question_ids:
                continue
            session.add(
                QuestionRecord(
                    id=question.id,
                    session_id=aggregate.id,
                    ordinal=question.ordinal,
                    status=question.status.value,
                    media_sha=question.media_sha,
                )
            )


def _aware_utc(value: datetime) -> datetime:
    """Normalize naive timestamps from SQLite fixtures and UTC from PostgreSQL."""
    if value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
