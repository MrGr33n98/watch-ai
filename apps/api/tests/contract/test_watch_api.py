import os
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import yaml
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.adapters.db.models import QuestionRecord, StudySessionRecord, UserRecord
from app.adapters.http.auth import WatchPrincipal, require_watch_principal
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


def create_owned_session(database_sessions: sessionmaker[Session]) -> tuple[UUID, UUID]:
    with database_sessions.begin() as database:
        user = UserRecord()
        study_session = StudySessionRecord(
            user=user,
            status="ready",
            expected_count=1,
            received_count=1,
        )
        question = QuestionRecord(
            session=study_session,
            ordinal=1,
            status="ready",
            statement_text="Compute the heat transfer rate.",
            problem_type="Fourier law",
            final_answer="2400",
            units="W",
            verification_status="verified",
        )
        database.add_all([study_session, question])
        database.flush()
        return user.id, study_session.id


def create_client(
    database_sessions: sessionmaker[Session],
    principal: WatchPrincipal | None = None,
) -> TestClient:
    application = create_app(app_env="test", session_factory=database_sessions)
    if principal is not None:
        application.dependency_overrides[require_watch_principal] = lambda: principal
    return TestClient(application)


def test_watch_routes_are_declared_in_the_openapi_contract() -> None:
    contract_path = (
        Path(__file__).resolve().parents[4]
        / "specs"
        / "001-watch-ai-mvp"
        / "contracts"
        / "openapi.yaml"
    )
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    expected_operations = {
        ("/v1/device-pairings", "post"): "pairWatch",
        ("/v1/devices/me", "delete"): "revokeWatchDevice",
        ("/v1/sessions", "get"): "listSessions",
        ("/v1/sessions/{session_id}", "get"): "getSession",
        ("/v1/sessions/{session_id}", "delete"): "deleteSession",
        ("/v1/sessions/{session_id}/questions/{ordinal}", "get"): "getQuestion",
    }
    application_openapi = create_app(app_env="test").openapi()

    for (path, method), operation_id in expected_operations.items():
        assert contract["paths"][path][method]["operationId"] == operation_id
        implementation = application_openapi["paths"][path][method]
        assert implementation["operationId"] == operation_id
        assert set(contract["paths"][path][method]["responses"]).issubset(
            implementation["responses"]
        )

    assert "bearerAuth" in application_openapi["components"]["securitySchemes"]


def test_watch_api_requires_authentication(
    database_sessions: sessionmaker[Session],
) -> None:
    response = create_client(database_sessions).get("/v1/sessions")

    assert response.status_code == 401
    assert response.json()["correlation_id"] == response.headers["X-Correlation-ID"]
    assert response.json() == {
        "code": "unauthorized",
        "message": "Watch authentication required",
        "correlation_id": response.headers["X-Correlation-ID"],
    }


def test_session_queries_are_scoped_to_the_authenticated_owner(
    database_sessions: sessionmaker[Session],
) -> None:
    owner_id, owned_session_id = create_owned_session(database_sessions)
    other_user_id, other_session_id = create_owned_session(database_sessions)
    client = create_client(
        database_sessions,
        principal=WatchPrincipal(user_id=owner_id, device_id=uuid4()),
    )

    listed = client.get("/v1/sessions")
    owned = client.get(f"/v1/sessions/{owned_session_id}")
    question = client.get(f"/v1/sessions/{owned_session_id}/questions/1")
    cross_owner = client.get(f"/v1/sessions/{other_session_id}")
    cross_owner_question = client.get(f"/v1/sessions/{other_session_id}/questions/1")

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [str(owned_session_id)]
    assert owned.status_code == 200
    assert [item["ordinal"] for item in owned.json()["questions"]] == [1]
    assert question.status_code == 200
    assert question.json()["verified"] is False
    assert question.json()["verification_status"] == "unverified"
    assert question.json()["steps"] == []
    assert cross_owner.status_code == 404
    assert cross_owner.json()["code"] == "not_found"
    assert cross_owner_question.status_code == 404
    assert other_user_id != owner_id
