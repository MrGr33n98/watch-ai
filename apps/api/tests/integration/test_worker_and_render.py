from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
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
from app.adapters.queue.fake_vision import FakeVisionProvider
from app.adapters.renderer.formulas import FormulaRenderer, PrivateFormulaAssetStore
from app.adapters.storage.jpeg import PillowJpegAdmission
from app.adapters.storage.private_media import PrivateMediaStore
from app.domain.ingestion.models import InboundMessage, InboundMessageState, OutboxEvent
from app.domain.interpretation.models import (
    ExtractedQuantity,
    InterpretationConfidence,
    InterpretedExercise,
)
from app.main import create_app
from app.worker import OutboxWorkerService, build_vision_provider

API_ROOT = Path(__file__).resolve().parents[2]
Q1_BYTES = (
    API_ROOT.parent.parent / "examples" / "synthetic_jpg" / "Q1_synthetic.jpg"
).read_bytes()


def test_worker_processes_outbox_renders_svg_and_enforces_owner_auth(tmp_path: Path) -> None:
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
    other_id = uuid4()
    session_id = uuid4()
    question_id = uuid4()
    owner_token = f"owner-render-{uuid4()}"
    other_token = f"other-render-{uuid4()}"
    now = datetime.now(UTC)

    media_store = PrivateMediaStore(tmp_path / "private-media")
    admitted = PillowJpegAdmission().admit(Q1_BYTES, "image/jpeg")
    media_store.store(admitted)

    message = InboundMessage(
        provider="waha",
        provider_message_id="worker-msg-1",
        sender_hmac="sender-hmac-1",
        provider_timestamp=now,
        received_at=now,
        session_id=session_id,
        question_ordinal=1,
        media_sha=admitted.sha256,
        state=InboundMessageState.QUEUED,
    )
    event = OutboxEvent.for_inbound_message(message)

    with session_factory.begin() as db:
        db.add_all([UserRecord(id=owner_id), UserRecord(id=other_id)])
        db.add(
            StudySessionRecord(
                id=session_id,
                user_id=owner_id,
                status="queued",
                expected_count=1,
                received_count=1,
                created_at=now,
            )
        )
        db.add(
            QuestionRecord(
                id=question_id,
                session_id=session_id,
                ordinal=1,
                status="uploaded",
                media_sha=admitted.sha256,
            )
        )
        db.add(
            InboundMessageRecord(
                id=message.id,
                provider=message.provider,
                provider_message_id=message.provider_message_id,
                sender_hmac=message.sender_hmac,
                media_sha=message.media_sha,
                session_id=session_id,
                question_ordinal=1,
                state=message.state.value,
                provider_timestamp=now,
                received_at=now,
            )
        )
        db.add(
            OutboxEventRecord(
                id=event.id,
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                event_type=event.event_type,
                payload=dict(event.payload),
                created_at=now,
                next_attempt_at=now,
                attempt_count=0,
            )
        )
        db.add_all(
            [
                WatchDeviceRecord(
                    id=uuid4(),
                    user_id=owner_id,
                    device_name="Watch Owner",
                    token_hash=hashlib.sha256(owner_token.encode()).hexdigest(),
                    scope="sessions:read",
                    created_at=now,
                    expires_at=now + timedelta(days=1),
                ),
                WatchDeviceRecord(
                    id=uuid4(),
                    user_id=other_id,
                    device_name="Watch Other",
                    token_hash=hashlib.sha256(other_token.encode()).hexdigest(),
                    scope="sessions:read",
                    created_at=now,
                    expires_at=now + timedelta(days=1),
                ),
            ]
        )

    vision = FakeVisionProvider(
        fixtures={
            admitted.sha256: InterpretedExercise(
                statement="Parede: k=1,2 W/(m K), A=10 m^2, deltaT=40 K, L=0,20 m.",
                problem_type="Fourier law",
                confidence=InterpretationConfidence.HIGH,
                needs_review=False,
                operation="fourier",
                parameters={
                    "k": ExtractedQuantity("1,2", "W/(m K)"),
                    "A": ExtractedQuantity("10", "m^2"),
                    "deltaT": ExtractedQuantity("40", "K"),
                    "L": ExtractedQuantity("0,20", "m"),
                },
            )
        }
    )
    render_store = PrivateFormulaAssetStore(tmp_path / "private-renders")
    worker = OutboxWorkerService(
        session_factory=session_factory,
        media_reader=media_store,
        vision_provider=vision,
        formula_renderer=FormulaRenderer(render_store),
    )

    summary = worker.run_once(now=now + timedelta(seconds=1))
    assert summary.claimed == 1
    assert summary.published == 1

    app = create_app(
        app_env="test",
        session_factory=session_factory,
        formula_asset_store=render_store,
    )
    with TestClient(app) as client:
        detail = client.get(
            f"/v1/sessions/{session_id}/questions/1",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert detail.status_code == 200
        payload = detail.json()
        assert payload["verified"] is True
        assert payload["final_answer"] == "2400"
        formula_step = next(step for step in payload["steps"] if step["kind"] == "formula")
        render_url = formula_step["render_url"]
        assert render_url == f"/v1/sessions/{session_id}/questions/1/steps/3/render"

        assert client.get(render_url).status_code == 401
        assert (
            client.get(render_url, headers={"Authorization": f"Bearer {other_token}"}).status_code
            == 404
        )
        svg_response = client.get(
            render_url,
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert svg_response.status_code == 200
        assert svg_response.headers["content-type"].startswith("image/svg+xml")
        assert svg_response.headers["x-content-type-options"] == "nosniff"
        assert "<svg " in svg_response.text

    engine.dispose()


def test_build_vision_provider_blocks_fake_in_production() -> None:
    try:
        build_vision_provider(
            environment={"APP_ENV": "production", "VISION_PROVIDER": "fake"}
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("Fake vision provider must be rejected in production")
