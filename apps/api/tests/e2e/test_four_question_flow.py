from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.db.base import Base
from app.adapters.db.ingestion import SqlAlchemyInboundMessageReader
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
from app.adapters.db.outbox_delivery import SqlAlchemyOutboxDeliveryRepository
from app.adapters.db.solutions import SqlAlchemySolutionRepository
from app.adapters.queue.audit import StructuredOutboxAudit
from app.adapters.queue.fake_vision import FakeVisionProvider
from app.adapters.queue.inbound_handler import (
    InboundMessageOutboxHandler,
)
from app.adapters.storage.jpeg import PillowJpegAdmission
from app.adapters.storage.private_media import PrivateMediaStore
from app.adapters.waha.webhook import WahaWebhookSettings
from app.application.outbox_dispatch import OutboxDispatcher, RetryPolicy
from app.application.solution_pipeline import SolutionPipeline
from app.application.solution_policy import SolutionPolicy
from app.domain.interpretation.models import InterpretationConfidence, InterpretedExercise
from app.domain.math_verification.quantities import PhysicalQuantity
from app.domain.math_verification.solution import ExerciseOperation, SolutionProblem
from app.main import create_app

API_ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_IMAGES = tuple(
    (API_ROOT.parent.parent / "examples" / "synthetic_jpg" / f"Q{ordinal}_synthetic.jpg")
    .read_bytes()
    for ordinal in range(1, 5)
)
WEBHOOK_KEY = "four-question-webhook-key-for-tests-32-bytes"
SENDER_KEY = "four-question-sender-hmac-key-for-tests-32-bytes"
SENDER = "5511999999999@c.us"
WATCH_TOKEN = "watch-token-for-four-question-flow-tests"  # noqa: S105


class FourPhotoDownloader:
    async def download(self, media_url: str, *, declared_mime: str):
        ordinal = int(Path(media_url).stem[1:])
        return PillowJpegAdmission().admit(SYNTHETIC_IMAGES[ordinal - 1], declared_mime)


class GoldenProblemMapper:
    def to_problem(self, exercise: InterpretedExercise, ordinal: int) -> SolutionProblem:
        assert exercise.statement is not None
        assert exercise.problem_type is not None
        match exercise.problem_type:
            case "Fourier law":
                return SolutionProblem(
                    ordinal=ordinal,
                    statement=exercise.statement,
                    problem_type=exercise.problem_type,
                    confidence=exercise.confidence,
                    needs_review=exercise.needs_review,
                    operation=ExerciseOperation.FOURIER,
                    parameters={
                        "k": PhysicalQuantity(Decimal("1.2"), "W/(m K)"),
                        "A": PhysicalQuantity(Decimal("10"), "m^2"),
                        "deltaT": PhysicalQuantity(Decimal("40"), "K"),
                        "L": PhysicalQuantity(Decimal("0.2"), "m"),
                    },
                )
            case "derivative":
                return SolutionProblem(
                    ordinal=ordinal,
                    statement=exercise.statement,
                    problem_type=exercise.problem_type,
                    confidence=exercise.confidence,
                    needs_review=exercise.needs_review,
                    operation=ExerciseOperation.DERIVATIVE,
                    expression="x**2 + 3*x",
                    variable="x",
                )
            case "definite integral":
                return SolutionProblem(
                    ordinal=ordinal,
                    statement=exercise.statement,
                    problem_type=exercise.problem_type,
                    confidence=exercise.confidence,
                    needs_review=exercise.needs_review,
                    operation=ExerciseOperation.DEFINITE_INTEGRAL,
                    expression="2*x",
                    variable="x",
                    lower="0",
                    upper="3",
                )
            case _:
                return SolutionProblem(
                    ordinal=ordinal,
                    statement=exercise.statement,
                    problem_type=exercise.problem_type,
                    confidence=exercise.confidence,
                    needs_review=exercise.needs_review,
                    operation=ExerciseOperation.UNSUPPORTED,
                )


def test_four_jpg_batch_is_verified_and_readable_from_watch_api(tmp_path: Path) -> None:
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
            WatchDeviceRecord.__table__,
            SolutionStepRecord.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner_id = uuid4()
    now = datetime.now(UTC)
    with session_factory.begin() as session:
        session.add(UserRecord(id=owner_id))
        session.add(
            WatchDeviceRecord(
                id=uuid4(),
                user_id=owner_id,
                device_name="Galaxy Watch4 test",
                token_hash=hashlib.sha256(WATCH_TOKEN.encode()).hexdigest(),
                scope="sessions:read",
                created_at=now,
                expires_at=now + timedelta(days=1),
            )
        )

    admission = PillowJpegAdmission()
    digests = [admission.admit(image, "image/jpeg").sha256 for image in SYNTHETIC_IMAGES]
    fixtures = {
        digests[0]: InterpretedExercise(
            "Parede: k=1,2 W/(m K), A=10 m^2, deltaT=40 K, L=0,20 m.",
            "Fourier law",
            InterpretationConfidence.HIGH,
            False,
        ),
        digests[1]: InterpretedExercise(
            "Derive f(x) = x^2 + 3x.",
            "derivative",
            InterpretationConfidence.HIGH,
            False,
        ),
        digests[2]: InterpretedExercise(
            "Calculate the definite integral of 2x from 0 to 3.",
            "definite integral",
            InterpretationConfidence.HIGH,
            False,
        ),
        digests[3]: InterpretedExercise(None, None, InterpretationConfidence.LOW, True),
    }
    media_store = PrivateMediaStore(tmp_path / "private-media")
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
            media_api_key="test-media-key",
        ),
        waha_media_downloader=FourPhotoDownloader(),
        waha_media_store=media_store,
    )

    def send_event(payload: dict[str, object]):
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
        started = send_event(
            {
                "id": "four-flow-start",
                "timestamp": int(now.timestamp()),
                "from": SENDER,
                "fromMe": False,
                "hasMedia": False,
                "body": "INICIAR 4",
            }
        )
        image_responses = [
            send_event(
                {
                    "id": f"four-flow-image-{ordinal}",
                    "timestamp": int(now.timestamp()) + ordinal,
                    "from": SENDER,
                    "fromMe": False,
                    "hasMedia": True,
                    "body": "",
                    "media": {
                        "url": f"https://waha.example.test/api/files/Q{ordinal}.jpg",
                        "mimetype": "image/jpeg",
                        "filename": f"Q{ordinal}.jpg",
                        "error": None,
                    },
                }
            )
            for ordinal in range(1, 5)
        ]

        mapper = GoldenProblemMapper()
        pipeline = SolutionPipeline(
            vision_provider=FakeVisionProvider(fixtures=fixtures),
            problem_mapper=mapper,
            solution_policy=SolutionPolicy(),
            result_repository=SqlAlchemySolutionRepository(session_factory),
        )
        handler = InboundMessageOutboxHandler(
            SqlAlchemyInboundMessageReader(session_factory),
            media_store,
            pipeline,
        )
        dispatcher = OutboxDispatcher(
            SqlAlchemyOutboxDeliveryRepository(session_factory),
            handler,
            StructuredOutboxAudit(),
            policy=RetryPolicy(max_attempts=3),
        )
        dispatch = dispatcher.dispatch_once(now=datetime.now(UTC) + timedelta(seconds=2))

        session_id = started.json()["session_id"]
        list_response = client.get(
            "/v1/sessions",
            headers={"Authorization": f"Bearer {WATCH_TOKEN}"},
        )
        session_response = client.get(
            f"/v1/sessions/{session_id}",
            headers={"Authorization": f"Bearer {WATCH_TOKEN}"},
        )
        q1_response = client.get(
            f"/v1/sessions/{session_id}/questions/1",
            headers={"Authorization": f"Bearer {WATCH_TOKEN}"},
        )
        q2_response = client.get(
            f"/v1/sessions/{session_id}/questions/2",
            headers={"Authorization": f"Bearer {WATCH_TOKEN}"},
        )
        q3_response = client.get(
            f"/v1/sessions/{session_id}/questions/3",
            headers={"Authorization": f"Bearer {WATCH_TOKEN}"},
        )
        q4_response = client.get(
            f"/v1/sessions/{session_id}/questions/4",
            headers={"Authorization": f"Bearer {WATCH_TOKEN}"},
        )

    assert started.status_code == 202
    assert all(response.status_code == 202 for response in image_responses)
    assert [response.json()["ordinal"] for response in image_responses] == [1, 2, 3, 4]
    assert dispatch.claimed == 4
    assert dispatch.published == 4
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == session_id
    assert session_response.status_code == 200
    session_data = session_response.json()
    assert session_data["status"] == "needs_review"
    assert [question["ordinal"] for question in session_data["questions"]] == [1, 2, 3, 4]
    assert [question["status"] for question in session_data["questions"]] == [
        "ready",
        "ready",
        "ready",
        "needs_review",
    ]
    assert q1_response.status_code == 200
    assert q1_response.json()["verified"] is True
    assert q1_response.json()["final_answer"] == "2400"
    assert q1_response.json()["units"] == "W"
    assert [step["ordinal"] for step in q1_response.json()["steps"]] == list(range(1, 8))
    assert q2_response.status_code == 200
    assert q2_response.json()["verified"] is True
    assert q2_response.json()["final_answer"] == "2*x + 3"
    assert q3_response.status_code == 200
    assert q3_response.json()["verified"] is True
    assert q3_response.json()["final_answer"] == "9"
    assert q4_response.status_code == 200
    assert q4_response.json()["verified"] is False
    assert q4_response.json()["verification_status"] == "inconclusive"
    assert q4_response.json()["final_answer"] is None
    assert not any(
        step["kind"] in {"calculation", "result"}
        for step in q4_response.json()["steps"]
    )

    with session_factory() as session:
        questions = session.scalars(
            select(QuestionRecord)
            .where(QuestionRecord.session_id == UUID(session_id))
            .order_by(QuestionRecord.ordinal)
        ).all()
    assert [question.final_answer for question in questions] == ["2400", "2*x + 3", "9", None]
    assert all(media_store.read(question.media_sha) for question in questions)
    engine.dispose()
