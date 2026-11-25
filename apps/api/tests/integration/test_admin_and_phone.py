from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from alembic import command
from app.adapters.db.base import Base
from app.adapters.db.models import (
    InboundMessageRecord,
    ModelUsageRecord,
    OutboxEventRecord,
    PairingCodeRecord,
    QuestionRecord,
    SenderSessionBindingRecord,
    SolutionStepRecord,
    StudySessionRecord,
    UserRecord,
    WatchDeviceRecord,
)
from app.adapters.storage.private_media import PrivateMediaStore
from app.main import create_app

API_ROOT = Path(__file__).resolve().parents[2]
Q1_BYTES = (
    API_ROOT.parent.parent / "examples" / "synthetic_jpg" / "Q1_synthetic.jpg"
).read_bytes()
Q2_BYTES = (
    API_ROOT.parent.parent / "examples" / "synthetic_jpg" / "Q2_synthetic.jpg"
).read_bytes()
ADMIN_SECRET = "operator-admin-secret-for-tests-32-bytes"  # noqa: S105


def _sqlite_sessions():
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
            PairingCodeRecord.__table__,
            WatchDeviceRecord.__table__,
            SolutionStepRecord.__table__,
            ModelUsageRecord.__table__,
        ],
    )
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def test_admin_and_phone_routes_fail_closed_without_key() -> None:
    engine, sessions = _sqlite_sessions()
    app = create_app(app_env="test", session_factory=sessions, admin_api_key="")
    with TestClient(app) as client:
        assert client.post("/v1/admin/users").status_code == 404
        assert client.get("/phone").status_code == 404
    engine.dispose()


def test_operator_can_provision_pair_remotely_revoke_lost_watch_and_upload_from_phone(
    tmp_path: Path,
) -> None:
    engine, sessions = _sqlite_sessions()
    media_store = PrivateMediaStore(tmp_path / "private-media")
    app = create_app(
        app_env="test",
        session_factory=sessions,
        waha_media_store=media_store,
        admin_api_key=ADMIN_SECRET,
    )
    admin_headers = {"X-Admin-Key": ADMIN_SECRET}

    with TestClient(app) as client:
        assert client.post("/v1/admin/users").status_code == 401
        assert client.post("/v1/admin/users", headers={"X-Admin-Key": "wrong"}).status_code == 401

        created_user = client.post("/v1/admin/users", headers=admin_headers)
        assert created_user.status_code == 201
        user_id = created_user.json()["user_id"]

        pairing = client.post(
            "/v1/admin/pairings",
            headers=admin_headers,
            json={"user_id": user_id, "ttl_minutes": 10},
        )
        assert pairing.status_code == 201
        raw_code = pairing.json()["pairing_code"]
        assert len(raw_code) == 8

        watch_pair = client.post(
            "/v1/device-pairings",
            json={
                "pairing_code": f"{raw_code[:4].lower()}-{raw_code[4:].lower()}",
                "device_name": "Galaxy Watch4 Lost",
            },
        )
        assert watch_pair.status_code == 201
        watch_token = watch_pair.json()["access_token"]
        device_id = watch_pair.json()["device_id"]
        watch_headers = {"Authorization": f"Bearer {watch_token}"}

        devices = client.get(f"/v1/admin/users/{user_id}/devices", headers=admin_headers)
        assert devices.status_code == 200
        assert devices.json()["items"][0]["device_id"] == device_id
        assert devices.json()["items"][0]["active"] is True

        upload = client.post(
            f"/v1/admin/users/{user_id}/batches/upload",
            headers=admin_headers,
            files=[
                ("files", ("Q1.jpg", Q1_BYTES, "image/jpeg")),
                ("files", ("Q2.jpg", Q2_BYTES, "image/jpeg")),
            ],
        )
        assert upload.status_code == 202
        session_id = upload.json()["session_id"]
        assert upload.json()["received_count"] == 2

        too_many = client.post(
            f"/v1/admin/users/{user_id}/batches/upload",
            headers=admin_headers,
            files=[("files", (f"Q{i}.jpg", Q1_BYTES, "image/jpeg")) for i in range(1, 6)],
        )
        assert too_many.status_code == 400

        assert client.get("/v1/sessions", headers=watch_headers).status_code == 200
        assert client.get(f"/v1/sessions/{session_id}", headers=watch_headers).status_code == 200

        revoked = client.delete(
            f"/v1/admin/users/{user_id}/devices/{device_id}",
            headers=admin_headers,
        )
        assert revoked.status_code == 204
        assert client.get("/v1/sessions", headers=watch_headers).status_code == 401
        assert (
            client.delete(
                f"/v1/admin/users/{uuid4()}/devices/{device_id}",
                headers=admin_headers,
            ).status_code
            == 404
        )

        budget = client.get("/v1/admin/budget", headers=admin_headers)
        assert budget.status_code == 200
        assert "spent_usd" in budget.json()

        phone_page = client.get("/phone")
        assert phone_page.status_code == 200
        assert "Watch AI" in phone_page.text
        assert ADMIN_SECRET not in phone_page.text

    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(OutboxEventRecord)) == 2
        assert db.scalar(select(func.count()).select_from(QuestionRecord)) == 2

    engine.dispose()


@pytest.fixture(scope="module")
def pg_sessions() -> Iterator[sessionmaker[Session]]:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL must point to a disposable PostgreSQL database")

    alembic_config = Config(str(API_ROOT / "alembic.ini"))
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")

    engine: Engine = create_engine(database_url)
    yield sessionmaker(bind=engine, expire_on_commit=False)

    command.downgrade(alembic_config, "base")
    engine.dispose()


def test_phone_batch_upload_and_revocation_on_postgresql(
    pg_sessions: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    media_store = PrivateMediaStore(tmp_path / "pg-private-media")
    app = create_app(
        app_env="test",
        session_factory=pg_sessions,
        waha_media_store=media_store,
        admin_api_key=ADMIN_SECRET,
    )
    admin_headers = {"X-Admin-Key": ADMIN_SECRET}

    with TestClient(app) as client:
        created_user = client.post("/v1/admin/users", headers=admin_headers)
        assert created_user.status_code == 201
        user_id = created_user.json()["user_id"]

        pairing = client.post(
            "/v1/admin/pairings",
            headers=admin_headers,
            json={"user_id": user_id, "ttl_minutes": 10},
        )
        assert pairing.status_code == 201
        raw_code = pairing.json()["pairing_code"]

        watch_pair = client.post(
            "/v1/device-pairings",
            json={"pairing_code": raw_code, "device_name": "Galaxy Watch4 PG"},
        )
        assert watch_pair.status_code == 201
        watch_token = watch_pair.json()["access_token"]
        device_id = watch_pair.json()["device_id"]
        watch_headers = {"Authorization": f"Bearer {watch_token}"}

        upload = client.post(
            f"/v1/admin/users/{user_id}/batches/upload",
            headers=admin_headers,
            files=[
                ("files", ("Q1.jpg", Q1_BYTES, "image/jpeg")),
                ("files", ("Q2.jpg", Q2_BYTES, "image/jpeg")),
            ],
        )
        assert upload.status_code == 202
        session_id = upload.json()["session_id"]
        assert upload.json()["received_count"] == 2

        detail = client.get(f"/v1/sessions/{session_id}", headers=watch_headers)
        assert detail.status_code == 200
        assert detail.json()["received_count"] == 2

        revoked = client.delete(
            f"/v1/admin/users/{user_id}/devices/{device_id}",
            headers=admin_headers,
        )
        assert revoked.status_code == 204
        assert client.get("/v1/sessions", headers=watch_headers).status_code == 401
