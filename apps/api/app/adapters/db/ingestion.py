from collections.abc import Sequence
from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.db.models import InboundMessageRecord, OutboxEventRecord
from app.application.ports import InboundMessageRepository, OutboxRepository
from app.domain.ingestion.models import (
    InboundMessage,
    InboundMessageState,
    OutboxEvent,
    order_messages_by_source_time,
)


class SqlAlchemyInboundMessageRepository(InboundMessageRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_if_absent(self, message: InboundMessage) -> tuple[InboundMessage, bool]:
        statement = (
            insert(InboundMessageRecord)
            .values(
                id=message.id,
                provider=message.provider,
                provider_message_id=message.provider_message_id,
                sender_hmac=message.sender_hmac,
                media_sha=message.media_sha,
                session_id=message.session_id,
                question_ordinal=message.question_ordinal,
                state=message.state.value,
                provider_timestamp=message.provider_timestamp,
                received_at=message.received_at,
            )
            .on_conflict_do_nothing(constraint="uq_inbound_provider_message")
            .returning(InboundMessageRecord.id)
        )
        inserted_id = self._session.execute(statement).scalar_one_or_none()
        if inserted_id is not None:
            return message, True

        existing = self._session.scalar(
            select(InboundMessageRecord).where(
                InboundMessageRecord.provider == message.provider,
                InboundMessageRecord.provider_message_id == message.provider_message_id,
            )
        )
        if existing is None:
            raise RuntimeError("A conflicting inbound message was not found")
        return self._to_domain(existing), False

    def list_for_session(self, session_id: UUID) -> Sequence[InboundMessage]:
        records = self._session.scalars(
            select(InboundMessageRecord)
            .where(InboundMessageRecord.session_id == session_id)
            .order_by(
                InboundMessageRecord.provider_timestamp,
                InboundMessageRecord.provider,
                InboundMessageRecord.provider_message_id,
            )
        ).all()
        return order_messages_by_source_time(self._to_domain(record) for record in records)

    def get_by_id(self, message_id: UUID) -> InboundMessage | None:
        record = self._session.get(InboundMessageRecord, message_id)
        return self._to_domain(record) if record is not None else None

    @staticmethod
    def _to_domain(record: InboundMessageRecord) -> InboundMessage:
        return InboundMessage(
            id=record.id,
            provider=record.provider,
            provider_message_id=record.provider_message_id,
            sender_hmac=record.sender_hmac,
            provider_timestamp=_aware_utc(record.provider_timestamp),
            received_at=_aware_utc(record.received_at),
            session_id=record.session_id,
            question_ordinal=record.question_ordinal,
            media_sha=record.media_sha,
            state=InboundMessageState(record.state),
        )


class SqlAlchemyInboundMessageReader:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_by_id(self, message_id: UUID) -> InboundMessage | None:
        with self._session_factory() as session:
            repository = SqlAlchemyInboundMessageRepository(session)
            return repository.get_by_id(message_id)


class SqlAlchemyOutboxRepository(OutboxRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, event: OutboxEvent) -> None:
        self._session.add(
            OutboxEventRecord(
                id=event.id,
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                event_type=event.event_type,
                payload=dict(event.payload),
                created_at=event.created_at,
                published_at=event.published_at,
                attempt_count=event.attempt_count,
            )
        )


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self._inbound_messages: SqlAlchemyInboundMessageRepository | None = None
        self._outbox: SqlAlchemyOutboxRepository | None = None
        self._committed = False

    @property
    def inbound_messages(self) -> SqlAlchemyInboundMessageRepository:
        if self._inbound_messages is None:
            raise RuntimeError("Unit of work must be entered before use")
        return self._inbound_messages

    @property
    def outbox(self) -> SqlAlchemyOutboxRepository:
        if self._outbox is None:
            raise RuntimeError("Unit of work must be entered before use")
        return self._outbox

    def __enter__(self) -> Self:
        if self._session is not None:
            raise RuntimeError("Unit of work is already active")
        self._session = self._session_factory()
        self._inbound_messages = SqlAlchemyInboundMessageRepository(self._session)
        self._outbox = SqlAlchemyOutboxRepository(self._session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        try:
            if exc_type is not None or not self._committed:
                self.rollback()
        finally:
            self._session.close()
            self._session = None
            self._inbound_messages = None
            self._outbox = None
            self._committed = False

    def commit(self) -> None:
        session = self._active_session()
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise
        self._committed = True

    def rollback(self) -> None:
        self._active_session().rollback()
        self._committed = False

    def _active_session(self) -> Session:
        if self._session is None:
            raise RuntimeError("Unit of work must be entered before use")
        return self._session


class SqlAlchemyUnitOfWorkFactory:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __call__(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self._session_factory)


def _aware_utc(value: datetime) -> datetime:
    if value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
