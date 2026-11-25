from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.adapters.db.delivery import SqlAlchemyDeliveryRepository
from app.adapters.db.models import (
    PairingCodeRecord,
    StudySessionRecord,
    UserRecord,
    WatchDeviceRecord,
)
from app.application.pairing import PairingCodeRejected, PairingService
from app.main import create_app


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


def create_user(database_sessions: sessionmaker[Session]) -> UUID:
    user_id = uuid4()
    with database_sessions.begin() as database:
        database.add(UserRecord(id=user_id))
    return user_id


def create_foreign_session(database_sessions: sessionmaker[Session], user_id: UUID) -> UUID:
    session_id = uuid4()
    with database_sessions.begin() as database:
        database.add(
            StudySessionRecord(
                id=session_id,
                user_id=user_id,
                status="collecting",
                expected_count=4,
                received_count=0,
            )
        )
    return session_id


def test_pairing_code_expires_and_can_only_be_redeemed_once(
    database_sessions: sessionmaker[Session],
) -> None:
    user_id = create_user(database_sessions)
    now = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)
    with database_sessions() as database:
        service = PairingService(SqlAlchemyDeliveryRepository(database))
        expired_code = service.create_pairing_code(
            user_id,
            expires_at=now - timedelta(seconds=1),
            now=now - timedelta(minutes=1),
        )
        valid_code = service.create_pairing_code(
            user_id,
            expires_at=now + timedelta(minutes=5),
            now=now,
        )

        with pytest.raises(PairingCodeRejected):
            service.pair(expired_code, "Galaxy Watch4", now=now)

        credential = service.pair(valid_code, "Galaxy Watch4", now=now)
        with pytest.raises(PairingCodeRejected):
            service.pair(valid_code, "Galaxy Watch4", now=now)

        pairing_code_hash = database.query(PairingCodeRecord).filter_by(user_id=user_id).all()
        device_record = database.query(WatchDeviceRecord).filter_by(id=credential.device_id).one()

    assert credential.user_id == user_id
    assert credential.access_token
    assert credential.scope == "sessions:read"
    assert all(record.code_hash not in {expired_code, valid_code} for record in pairing_code_hash)
    assert device_record.token_hash != credential.access_token
    assert device_record.device_name == "Galaxy Watch4"


def test_watch_access_is_owner_scoped_and_revocation_takes_effect(
    database_sessions: sessionmaker[Session],
) -> None:
    user_id = create_user(database_sessions)
    foreign_user_id = create_user(database_sessions)
    foreign_session_id = create_foreign_session(database_sessions, foreign_user_id)
    now = datetime.now(UTC)
    with database_sessions() as database:
        service = PairingService(SqlAlchemyDeliveryRepository(database))
        code = service.create_pairing_code(
            user_id,
            expires_at=now + timedelta(minutes=5),
            now=now,
        )
        credential = service.pair(code, "Galaxy Watch4", now=now)

    application = create_app("test", session_factory=database_sessions)
    with TestClient(application) as client:
        headers = {"Authorization": f"Bearer {credential.access_token}"}
        assert client.get("/v1/sessions", headers=headers).status_code == 200
        assert (
            client.get(f"/v1/sessions/{foreign_session_id}", headers=headers).status_code == 404
        )
        assert client.delete("/v1/devices/me", headers=headers).status_code == 204
        assert client.get("/v1/sessions", headers=headers).status_code == 401
        assert client.get("/v1/sessions").status_code == 401


def test_pairing_endpoint_returns_scoped_token(
    database_sessions: sessionmaker[Session],
) -> None:
    user_id = create_user(database_sessions)
    now = datetime.now(UTC)
    with database_sessions() as database:
        service = PairingService(SqlAlchemyDeliveryRepository(database))
        code = service.create_pairing_code(
            user_id,
            expires_at=now + timedelta(minutes=5),
            now=now,
        )

    application = create_app("test", session_factory=database_sessions)
    with TestClient(application) as client:
        paired = client.post(
            "/v1/device-pairings",
            json={"pairing_code": code, "device_name": "Galaxy Watch4"},
        )
        assert paired.status_code == 201
        assert paired.json()["scope"] == "sessions:read"
        assert paired.json()["access_token"]
        reused = client.post(
            "/v1/device-pairings",
            json={"pairing_code": code, "device_name": "Galaxy Watch4"},
        )
        assert reused.status_code == 401
