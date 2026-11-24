import hashlib
import hmac
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.db.base import Base
from app.adapters.db.batches import SqlAlchemyBatchRepository
from app.adapters.db.models import (
    InboundMessageRecord,
    OutboxEventRecord,
    QuestionRecord,
    SenderSessionBindingRecord,
    StudySessionRecord,
    UserRecord,
)
from app.adapters.storage.jpeg import PillowJpegAdmission
from app.adapters.waha.webhook import WahaWebhookSettings
from app.application.batches import BatchSessionService
from app.application.ingestion import IngestionOutcome, IngestionResult
from app.domain.ingestion.models import InboundMessage
from app.main import create_app

API_ROOT = Path(__file__).resolve().parents[2]
JPEG_FIXTURE = (
    API_ROOT.parent.parent / "examples" / "synthetic_jpg" / "Q1_synthetic.jpg"
).read_bytes()
WEBHOOK_KEY = "batch-webhook-key-for-tests-32-bytes-minimum"
SENDER_KEY = "batch-sender-key-for-tests-32-bytes-minimum"
SENDER = "5511999999999@c.us"


class RecordingIngestor:
    def __init__(self) -> None:
        self.messages: list[InboundMessage] = []
        self.seen: set[tuple[str, str]] = set()

    def execute(self, message: InboundMessage) -> IngestionResult:
        self.messages.append(message)
        key = (message.provider, message.provider_message_id)
        if key in self.seen:
            return IngestionResult(IngestionOutcome.DUPLICATE, str(message.id))
        self.seen.add(key)
        return IngestionResult(IngestionOutcome.ACCEPTED, str(message.id))


class FixtureDownloader:
    async def download(self, media_url: str, *, declared_mime: str):
        del media_url
        return PillowJpegAdmission().admit(JPEG_FIXTURE, declared_mime)


class NoopStore:
    def store(self, image) -> None:
        del image


def test_sql_batch_repository_persists_owner_order_and_incomplete_close() -> None:
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
            SenderSessionBindingRecord.__table__,
            InboundMessageRecord.__table__,
            OutboxEventRecord.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner_id = uuid4()
    with session_factory.begin() as session:
        session.add(UserRecord(id=owner_id))

    service = BatchSessionService(SqlAlchemyBatchRepository(session_factory))
    sender_hmac = "a" * 64
    now = datetime(2026, 11, 23, 12, tzinfo=UTC)
    started = service.start(sender_hmac, owner_id, expected_count=4, now=now)
    service.add_image(sender_hmac, "sha-q1", now=now)
    service.add_image(sender_hmac, "sha-q2", now=now)
    service.finish(sender_hmac, now=now)

    with session_factory() as session:
        stored = session.get(StudySessionRecord, started.session_id)
        questions = session.scalars(
            select(QuestionRecord)
            .where(QuestionRecord.session_id == started.session_id)
            .order_by(QuestionRecord.ordinal)
        ).all()
        binding_count = session.scalar(
            select(func.count()).select_from(SenderSessionBindingRecord)
        )

    assert stored is not None
    assert stored.user_id == owner_id
    assert stored.status == "queued"
    assert stored.received_count == 2
    assert [(question.ordinal, question.media_sha) for question in questions] == [
        (1, "sha-q1"),
        (2, "sha-q2"),
    ]
    assert binding_count == 0
    engine.dispose()


def test_waha_commands_and_images_create_owned_ordered_session() -> None:
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
            SenderSessionBindingRecord.__table__,
            InboundMessageRecord.__table__,
            OutboxEventRecord.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner_id = uuid4()
    with session_factory.begin() as session:
        session.add(UserRecord(id=owner_id))
    ingestor = RecordingIngestor()
    application = create_app(
        app_env="test",
        session_factory=session_factory,
        waha_settings=WahaWebhookSettings(
            enabled=True,
            webhook_hmac_secret=WEBHOOK_KEY,
            sender_hash_secret=SENDER_KEY,
            allowed_sessions=frozenset({"watch-ai-dev"}),
            allowed_senders=frozenset({SENDER}),
            sender_owner_ids={SENDER: owner_id},
            media_base_url="https://waha.example.test",
            media_api_key="test-key",
        ),
        waha_ingestion=ingestor,
        waha_media_downloader=FixtureDownloader(),
        waha_media_store=NoopStore(),
    )

    def post(payload: dict[str, object]):
        body = json.dumps(
            {"event": "message", "session": "watch-ai-dev", "payload": payload}
        ).encode()
        signature = hmac.new(WEBHOOK_KEY.encode(), body, hashlib.sha512).hexdigest()
        return client.post(
            "/waha/webhook",
            content=body,
            headers={
                "X-Webhook-Hmac-Algorithm": "sha512",
                "X-Webhook-Hmac": signature,
            },
        )

    with TestClient(application) as client:
        started = post(
            {
                "id": "command-start",
                "timestamp": 1795450000,
                "from": SENDER,
                "fromMe": False,
                "hasMedia": False,
                "body": "INICIAR 3",
            }
        )
        first = post(_image_event_payload("image-one", "Q1.jpg"))
        second = post(_image_event_payload("image-two", "Q2.jpg"))
        finalized = post(
            {
                "id": "command-finish",
                "timestamp": 1795450003,
                "from": SENDER,
                "fromMe": False,
                "hasMedia": False,
                "body": "FINALIZAR",
            }
        )

    assert started.status_code == 202
    assert started.json()["expected_count"] == 3
    assert first.status_code == 202
    assert second.status_code == 202
    assert finalized.status_code == 202
    session_id = started.json()["session_id"]
    assert first.json()["ordinal"] == 1
    assert second.json()["ordinal"] == 2
    with session_factory() as session:
        stored = session.get(StudySessionRecord, UUID(session_id))
        questions = session.scalars(
            select(QuestionRecord)
            .where(QuestionRecord.session_id == UUID(session_id))
            .order_by(QuestionRecord.ordinal)
        ).all()
    assert stored is not None
    assert stored.user_id == owner_id
    assert stored.expected_count == 3
    assert stored.received_count == 2
    assert stored.status == "queued"
    assert [question.ordinal for question in questions] == [1, 2]
    assert ingestor.messages == []
    with session_factory() as session:
        inbound = session.scalars(
            select(InboundMessageRecord)
            .where(InboundMessageRecord.session_id == UUID(session_id))
            .order_by(InboundMessageRecord.question_ordinal)
        ).all()
        outbox_count = session.scalar(select(func.count()).select_from(OutboxEventRecord))
    assert [message.question_ordinal for message in inbound] == [1, 2]
    assert outbox_count == 2
    engine.dispose()


def test_ten_duplicate_webhooks_create_one_question_and_one_outbox_event() -> None:
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
            SenderSessionBindingRecord.__table__,
            InboundMessageRecord.__table__,
            OutboxEventRecord.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner_id = uuid4()
    with session_factory.begin() as session:
        session.add(UserRecord(id=owner_id))
    application = create_app(
        app_env="test",
        session_factory=session_factory,
        waha_settings=WahaWebhookSettings(
            enabled=True,
            webhook_hmac_secret=WEBHOOK_KEY,
            sender_hash_secret=SENDER_KEY,
            allowed_sessions=frozenset({"watch-ai-dev"}),
            allowed_senders=frozenset({SENDER}),
            sender_owner_ids={SENDER: owner_id},
            media_base_url="https://waha.example.test",
            media_api_key="test-key",
        ),
        waha_media_downloader=FixtureDownloader(),
        waha_media_store=NoopStore(),
    )
    start_event = {
        "id": "command-start-duplicate-case",
        "timestamp": 1795450000,
        "from": SENDER,
        "fromMe": False,
        "hasMedia": False,
        "body": "INICIAR 4",
    }
    image_event = _image_event_payload("same-image-event", "Q1.jpg")

    with TestClient(application) as client:
        started = _post_signed(client, start_event)
        responses = [_post_signed(client, image_event) for _ in range(10)]

    assert started.status_code == 202
    assert responses[0].status_code == 202
    assert all(response.status_code == 200 for response in responses[1:])
    assert all(response.json()["status"] == "duplicate" for response in responses[1:])
    with session_factory() as session:
        session_id = UUID(started.json()["session_id"])
        question_count = session.scalar(
            select(func.count()).select_from(QuestionRecord).where(
                QuestionRecord.session_id == session_id
            )
        )
        inbound_count = session.scalar(
            select(func.count()).select_from(InboundMessageRecord)
        )
        outbox_count = session.scalar(select(func.count()).select_from(OutboxEventRecord))
    assert question_count == 1
    assert inbound_count == 1
    assert outbox_count == 1
    engine.dispose()


def _image_event_payload(message_id: str, filename: str) -> dict[str, object]:
    return {
        "id": message_id,
        "timestamp": 1795450001 if message_id == "image-one" else 1795450002,
        "from": SENDER,
        "fromMe": False,
        "hasMedia": True,
        "body": "",
        "media": {
            "url": f"https://waha.example.test/api/files/{message_id}.jpg",
            "mimetype": "image/jpeg",
            "filename": filename,
            "error": None,
        },
    }


def _post_signed(client: TestClient, payload: dict[str, object]):
    body = json.dumps(
        {"event": "message", "session": "watch-ai-dev", "payload": payload}
    ).encode()
    signature = hmac.new(WEBHOOK_KEY.encode(), body, hashlib.sha512).hexdigest()
    return client.post(
        "/waha/webhook",
        content=body,
        headers={
            "X-Webhook-Hmac-Algorithm": "sha512",
            "X-Webhook-Hmac": signature,
        },
    )
