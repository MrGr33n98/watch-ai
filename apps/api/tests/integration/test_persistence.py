import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.adapters.db.ingestion import SqlAlchemyUnitOfWorkFactory
from app.adapters.db.models import (
    InboundMessageRecord,
    OutboxEventRecord,
    QuestionRecord,
    StudySessionRecord,
    UserRecord,
)
from app.application.ingestion import IngestInboundMessage, IngestionOutcome
from app.domain.ingestion.models import InboundMessage


@pytest.fixture(scope="module")
def database_sessions() -> Iterator[sessionmaker[Session]]:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL must point to a disposable PostgreSQL database")

    api_root = Path(__file__).resolve().parents[2]
    alembic_config = Config(str(api_root / "alembic.ini"))
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")

    engine: Engine = create_engine(database_url)
    yield sessionmaker(bind=engine, expire_on_commit=False)

    command.downgrade(alembic_config, "base")
    engine.dispose()


def create_session(
    database_sessions: sessionmaker[Session],
    *,
    expected_count: int = 4,
    received_count: int = 0,
) -> tuple[UUID, UUID]:
    with database_sessions.begin() as database:
        user = UserRecord(id=uuid4())
        study_session = StudySessionRecord(
            id=uuid4(),
            user=user,
            status="collecting",
            expected_count=expected_count,
            received_count=received_count,
        )
        database.add(study_session)
        database.flush()
        return user.id, study_session.id


def test_question_order_is_unique_within_a_session(
    database_sessions: sessionmaker[Session],
) -> None:
    _, session_id = create_session(database_sessions)

    with pytest.raises(IntegrityError):
        with database_sessions.begin() as database:
            database.add_all(
                [
                    QuestionRecord(session_id=session_id, ordinal=1, status="uploaded"),
                    QuestionRecord(session_id=session_id, ordinal=1, status="uploaded"),
                ]
            )
            database.flush()


def test_question_requires_an_existing_session(
    database_sessions: sessionmaker[Session],
) -> None:
    with pytest.raises(IntegrityError):
        with database_sessions.begin() as database:
            database.add(QuestionRecord(session_id=uuid4(), ordinal=1, status="uploaded"))
            database.flush()


@pytest.mark.parametrize("expected_count", [0, 5])
def test_expected_question_count_is_constrained_to_one_through_four(
    database_sessions: sessionmaker[Session],
    expected_count: int,
) -> None:
    with pytest.raises(IntegrityError):
        create_session(database_sessions, expected_count=expected_count)


@pytest.mark.parametrize("expected_count,received_count", [(4, 5), (1, 2)])
def test_received_question_count_is_within_supported_and_expected_bounds(
    database_sessions: sessionmaker[Session],
    expected_count: int,
    received_count: int,
) -> None:
    with pytest.raises(IntegrityError):
        create_session(
            database_sessions,
            expected_count=expected_count,
            received_count=received_count,
        )


@pytest.mark.parametrize("ordinal", [0, 5])
def test_question_ordinal_is_constrained_to_one_through_four(
    database_sessions: sessionmaker[Session],
    ordinal: int,
) -> None:
    _, session_id = create_session(database_sessions)

    with pytest.raises(IntegrityError):
        with database_sessions.begin() as database:
            database.add(QuestionRecord(session_id=session_id, ordinal=ordinal, status="uploaded"))
            database.flush()


def test_study_session_requires_an_existing_user(
    database_sessions: sessionmaker[Session],
) -> None:
    with pytest.raises(IntegrityError):
        with database_sessions.begin() as database:
            database.add(
                StudySessionRecord(
                    user_id=uuid4(),
                    status="created",
                    expected_count=4,
                    received_count=0,
                )
            )
            database.flush()


def test_duplicate_inbound_event_persists_one_row_and_one_outbox_event(
    database_sessions: sessionmaker[Session],
) -> None:
    handler = IngestInboundMessage(SqlAlchemyUnitOfWorkFactory(database_sessions))
    message = InboundMessage(
        provider="waha",
        provider_message_id="duplicate-event",
        sender_hmac="sender-hmac",
        provider_timestamp=datetime.now(UTC),
    )

    first = handler.execute(message)
    duplicate = handler.execute(message)

    assert first.outcome is IngestionOutcome.ACCEPTED
    assert duplicate.outcome is IngestionOutcome.DUPLICATE
    with database_sessions() as database:
        message_count = database.scalar(select(func.count()).select_from(InboundMessageRecord))
        event_count = database.scalar(select(func.count()).select_from(OutboxEventRecord))

    assert message_count == 1
    assert event_count == 1


def test_database_repository_orders_out_of_order_webhooks_by_provider_timestamp(
    database_sessions: sessionmaker[Session],
) -> None:
    _, session_id = create_session(database_sessions)
    handler = IngestInboundMessage(SqlAlchemyUnitOfWorkFactory(database_sessions))
    earlier_timestamp = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)
    earlier = InboundMessage(
        provider="waha",
        provider_message_id="earlier-event",
        sender_hmac="sender-hmac",
        provider_timestamp=earlier_timestamp,
        session_id=session_id,
    )
    later = InboundMessage(
        provider="waha",
        provider_message_id="later-event",
        sender_hmac="sender-hmac",
        provider_timestamp=earlier_timestamp + timedelta(seconds=1),
        session_id=session_id,
    )
    handler.execute(later)
    handler.execute(earlier)

    with SqlAlchemyUnitOfWorkFactory(database_sessions)() as unit_of_work:
        ordered_messages = unit_of_work.inbound_messages.list_for_session(session_id)

    assert [message.provider_message_id for message in ordered_messages] == [
        "earlier-event",
        "later-event",
    ]
