from __future__ import annotations

import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.db.base import Base
from app.adapters.db.models import (
    InboundMessageRecord,
    OutboxEventRecord,
    QuestionRecord,
    SenderSessionBindingRecord,
    SolutionStepRecord,
    StudySessionRecord,
    UserRecord,
    WatchDeviceRecord,
)
from app.adapters.db.retention import SqlAlchemySessionRetentionRepository
from app.adapters.storage.jpeg import PillowJpegAdmission
from app.adapters.storage.private_media import PrivateMediaStore
from app.application.retention import SessionRetentionPolicy, SessionRetentionService
from app.main import create_app

API_ROOT = Path(__file__).resolve().parents[2]
JPEG_BYTES = (
    API_ROOT.parent.parent / "examples" / "synthetic_jpg" / "Q1_synthetic.jpg"
).read_bytes()


@pytest.fixture
def retention_database(
    tmp_path: Path,
) -> Iterator[tuple[sessionmaker[Session], PrivateMediaStore, str, Path]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            UserRecord.__table__,
            StudySessionRecord.__table__,
            QuestionRecord.__table__,
            SolutionStepRecord.__table__,
            SenderSessionBindingRecord.__table__,
            InboundMessageRecord.__table__,
            OutboxEventRecord.__table__,
            WatchDeviceRecord.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    media_store = PrivateMediaStore(tmp_path / "private-media")
    admitted = PillowJpegAdmission().admit(JPEG_BYTES, "image/jpeg")
    media_store.store(admitted)
    media_path = tmp_path / "private-media" / admitted.sha256[:2] / f"{admitted.sha256}.jpg"
    try:
        yield session_factory, media_store, admitted.sha256, media_path
    finally:
        engine.dispose()


def _seed_session(
    session: Session,
    *,
    owner_id: UUID,
    session_id: UUID,
    media_sha: str,
    created_at: datetime,
    completed_at: datetime | None = None,
    token: str,
) -> UUID:
    session.add(UserRecord(id=owner_id))
    session.add(
        StudySessionRecord(
            id=session_id,
            user_id=owner_id,
            status="ready",
            expected_count=1,
            received_count=1,
            created_at=created_at,
            completed_at=completed_at or created_at,
        )
    )
    question_id = uuid4()
    session.add(
        QuestionRecord(
            id=question_id,
            session_id=session_id,
            ordinal=1,
            status="ready",
            media_sha=media_sha,
            statement_text="Question with retained image",
            problem_type="derivative",
            confidence="high",
            verification_status="verified",
            final_answer="2*x",
            created_at=created_at,
            updated_at=completed_at or created_at,
        )
    )
    session.add(
        SolutionStepRecord(
            id=uuid4(),
            question_id=question_id,
            ordinal=1,
            kind="result",
            title="Result",
            plain_text="2*x",
            verified=True,
        )
    )
    message_id = uuid4()
    session.add(
        InboundMessageRecord(
            id=message_id,
            provider="waha",
            provider_message_id=f"message-{session_id}",
            sender_hmac=f"sender-{session_id}",
            media_sha=media_sha,
            session_id=session_id,
            question_ordinal=1,
            state="processed",
            provider_timestamp=created_at,
            received_at=created_at,
        )
    )
    session.add(
        OutboxEventRecord(
            id=uuid4(),
            aggregate_type="inbound_message",
            aggregate_id=message_id,
            event_type="inbound_message.accepted",
            payload={"message_id": str(message_id), "session_id": str(session_id)},
            created_at=created_at,
            next_attempt_at=created_at,
        )
    )
    session.add(
        WatchDeviceRecord(
            id=uuid4(),
            user_id=owner_id,
            device_name="Retention test watch",
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            scope="sessions:read",
            created_at=created_at,
            expires_at=created_at + timedelta(days=30),
        )
    )
    return message_id


def test_owner_delete_purges_session_steps_and_only_unreferenced_media(
    retention_database: tuple[sessionmaker[Session], PrivateMediaStore, str, Path],
) -> None:
    session_factory, media_store, media_sha, media_path = retention_database
    now = datetime.now(UTC)
    owner_id, foreign_owner_id = uuid4(), uuid4()
    owner_session_id, foreign_session_id = uuid4(), uuid4()
    owner_token, foreign_token = "owner-token", "foreign-token"
    with session_factory.begin() as session:
        owner_message_id = _seed_session(
            session,
            owner_id=owner_id,
            session_id=owner_session_id,
            media_sha=media_sha,
            created_at=now,
            token=owner_token,
        )
        foreign_message_id = _seed_session(
            session,
            owner_id=foreign_owner_id,
            session_id=foreign_session_id,
            media_sha=media_sha,
            created_at=now,
            token=foreign_token,
        )

    application = create_app(
        app_env="test",
        session_factory=session_factory,
        waha_media_store=media_store,
    )
    with TestClient(application) as client:
        assert client.delete(f"/v1/sessions/{owner_session_id}").status_code == 401
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        foreign_headers = {"Authorization": f"Bearer {foreign_token}"}
        assert client.delete(
            f"/v1/sessions/{foreign_session_id}", headers=owner_headers
        ).status_code == 404
        deleted = client.delete(f"/v1/sessions/{owner_session_id}", headers=owner_headers)
        assert deleted.status_code == 204
        assert (
            client.get(f"/v1/sessions/{owner_session_id}", headers=owner_headers).status_code
            == 404
        )
        assert media_path.exists()

        with session_factory() as session:
            assert session.get(StudySessionRecord, owner_session_id) is None
            assert (
                session.scalar(
                    select(QuestionRecord.id).where(
                        QuestionRecord.session_id == owner_session_id
                    )
                )
                is None
            )
            foreign_question_id = session.scalar(
                select(QuestionRecord.id).where(
                    QuestionRecord.session_id == foreign_session_id
                )
            )
            assert foreign_question_id is not None
            assert session.scalar(
                select(func.count())
                .select_from(SolutionStepRecord)
                .where(SolutionStepRecord.question_id == foreign_question_id)
            ) == 1
            owner_message = session.get(InboundMessageRecord, owner_message_id)
            assert owner_message is not None
            assert owner_message.session_id is None
            assert owner_message.media_sha is None
            assert owner_message.state == "rejected"
            assert session.scalar(
                select(func.count())
                .select_from(OutboxEventRecord)
                .where(OutboxEventRecord.aggregate_id == owner_message_id)
            ) == 0
            assert session.get(InboundMessageRecord, foreign_message_id) is not None

        assert client.delete(
            f"/v1/sessions/{foreign_session_id}", headers=foreign_headers
        ).status_code == 204
        assert not media_path.exists()
        with session_factory() as session:
            assert session.scalar(select(func.count()).select_from(QuestionRecord)) == 0
            assert session.scalar(select(func.count()).select_from(SolutionStepRecord)) == 0


def test_configured_retention_purges_expired_session_assets(
    retention_database: tuple[sessionmaker[Session], PrivateMediaStore, str, Path],
) -> None:
    session_factory, media_store, media_sha, media_path = retention_database
    now = datetime.now(UTC)
    owner_id, session_id, token = uuid4(), uuid4(), "expired-session-token"
    with session_factory.begin() as session:
        _seed_session(
            session,
            owner_id=owner_id,
            session_id=session_id,
            media_sha=media_sha,
            created_at=now - timedelta(days=31),
            token=token,
        )

    policy = SessionRetentionPolicy.from_environment(
        {"MEDIA_RETENTION_HOURS": "24", "SESSION_RETENTION_DAYS": "30"}
    )
    with session_factory() as session:
        service = SessionRetentionService(
            SqlAlchemySessionRetentionRepository(session),
            media_store,
            policy,
        )
        result = service.purge_expired(now=now)

    assert result.deleted_sessions == 1
    assert result.purged_media == 1
    assert not media_path.exists()
    with session_factory() as session:
        assert session.get(StudySessionRecord, session_id) is None


def test_raw_media_expires_before_the_session_and_keeps_only_its_digest(
    retention_database: tuple[sessionmaker[Session], PrivateMediaStore, str, Path],
) -> None:
    session_factory, media_store, media_sha, media_path = retention_database
    now = datetime.now(UTC)
    owner_id, session_id = uuid4(), uuid4()
    with session_factory.begin() as session:
        message_id = _seed_session(
            session,
            owner_id=owner_id,
            session_id=session_id,
            media_sha=media_sha,
            created_at=now - timedelta(days=2),
            token=f"retained-session-{uuid4()}",
        )

    policy = SessionRetentionPolicy(media_retention_hours=24, session_retention_days=30)
    with session_factory() as session:
        service = SessionRetentionService(
            SqlAlchemySessionRetentionRepository(session),
            media_store,
            policy,
        )
        result = service.purge_expired(now=now)

    assert result.deleted_sessions == 0
    assert result.purged_media == 1
    assert not media_path.exists()
    with session_factory() as session:
        question = session.scalar(
            select(QuestionRecord).where(QuestionRecord.session_id == session_id)
        )
        message = session.get(InboundMessageRecord, message_id)
        assert session.get(StudySessionRecord, session_id) is not None
        assert question is not None and question.media_sha is None
        assert message is not None and message.media_sha == media_sha


def test_session_retention_starts_from_completion_time(
    retention_database: tuple[sessionmaker[Session], PrivateMediaStore, str, Path],
) -> None:
    session_factory, media_store, media_sha, media_path = retention_database
    now = datetime.now(UTC)
    retained_session_id, expired_session_id = uuid4(), uuid4()
    with session_factory.begin() as session:
        _seed_session(
            session,
            owner_id=uuid4(),
            session_id=retained_session_id,
            media_sha=media_sha,
            created_at=now - timedelta(days=60),
            completed_at=now - timedelta(days=20),
            token=f"retained-{uuid4()}",
        )
        _seed_session(
            session,
            owner_id=uuid4(),
            session_id=expired_session_id,
            media_sha=media_sha,
            created_at=now - timedelta(days=45),
            completed_at=now - timedelta(days=31),
            token=f"expired-{uuid4()}",
        )

    policy = SessionRetentionPolicy(media_retention_hours=24, session_retention_days=30)
    with session_factory() as session:
        service = SessionRetentionService(
            SqlAlchemySessionRetentionRepository(session),
            media_store,
            policy,
        )
        result = service.purge_expired(now=now)

    assert result.deleted_sessions == 1
    assert result.purged_media == 1
    assert not media_path.exists()
    with session_factory() as session:
        assert session.get(StudySessionRecord, retained_session_id) is not None
        assert session.get(StudySessionRecord, expired_session_id) is None
