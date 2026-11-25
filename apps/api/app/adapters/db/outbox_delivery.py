"""SQLAlchemy claim, retry, publish, and dead-letter operations for outbox rows."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.db.models import OutboxEventRecord
from app.application.outbox_dispatch import OutboxDeliveryRepository
from app.domain.ingestion.models import OutboxEvent


class SqlAlchemyOutboxDeliveryRepository(OutboxDeliveryRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def claim_due(
        self,
        *,
        now: datetime,
        limit: int,
        lease: timedelta,
    ) -> tuple[OutboxEvent, ...]:
        with self._session_factory() as session, session.begin():
            records = session.scalars(
                select(OutboxEventRecord)
                .where(
                    OutboxEventRecord.published_at.is_(None),
                    OutboxEventRecord.dead_lettered_at.is_(None),
                    OutboxEventRecord.next_attempt_at <= now,
                    or_(
                        OutboxEventRecord.locked_until.is_(None),
                        OutboxEventRecord.locked_until <= now,
                    ),
                )
                .order_by(OutboxEventRecord.created_at, OutboxEventRecord.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            ).all()
            for record in records:
                record.attempt_count += 1
                record.locked_until = now + lease
            events = tuple(self._to_domain(record) for record in records)
        return events

    def mark_published(self, event_id: UUID, *, at: datetime) -> None:
        with self._session_factory() as session, session.begin():
            record = session.get(OutboxEventRecord, event_id)
            if record is None or record.dead_lettered_at is not None:
                return
            record.published_at = at
            record.locked_until = None

    def record_failure(
        self,
        event_id: UUID,
        *,
        attempt_count: int,
        error_code: str,
        next_attempt_at: datetime | None,
        dead_lettered_at: datetime | None,
    ) -> None:
        with self._session_factory() as session, session.begin():
            record = session.get(OutboxEventRecord, event_id)
            if record is None or record.published_at is not None:
                return
            record.attempt_count = attempt_count
            record.last_error_code = error_code[:48]
            record.next_attempt_at = next_attempt_at or record.next_attempt_at
            record.dead_lettered_at = dead_lettered_at
            record.locked_until = None

    @staticmethod
    def _to_domain(record: OutboxEventRecord) -> OutboxEvent:
        return OutboxEvent(
            id=record.id,
            aggregate_type=record.aggregate_type,
            aggregate_id=record.aggregate_id,
            event_type=record.event_type,
            payload=record.payload,
            created_at=_aware_utc(record.created_at),
            published_at=(
                _aware_utc(record.published_at) if record.published_at is not None else None
            ),
            attempt_count=record.attempt_count,
        )


def _aware_utc(value: datetime) -> datetime:
    if value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
