from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from decimal import Decimal

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.db.base import Base
from app.adapters.db.models import ModelUsageRecord
from app.adapters.db.telemetry import SqlAlchemyMonthlyModelBudget
from app.adapters.openrouter.provider import OpenRouterVisionProvider
from app.domain.ingestion.models import InboundMessage
from app.infrastructure.telemetry import MonthlyModelBudget
from app.main import create_app


def test_request_logs_are_correlated_and_exclude_private_request_data(caplog) -> None:
    application = create_app(app_env="test")
    caplog.set_level(logging.INFO, logger="watch_ai.http")
    private_query = "query-secret-value"
    authorization_header = "Bearer bearer-private-value"

    with TestClient(application) as client:
        response = client.get(
            f"/route-that-does-not-exist?access_token={private_query}",
            headers={
                "Authorization": authorization_header,
                "X-Correlation-ID": "trace-allowed-123",
            },
        )

    assert response.status_code == 404
    assert response.headers["X-Correlation-ID"] == "trace-allowed-123"
    assert response.json()["correlation_id"] == "trace-allowed-123"
    assert private_query not in caplog.text
    assert authorization_header not in caplog.text
    record = next(record for record in caplog.records if record.name == "watch_ai.http")
    assert record.route == "unmatched"
    assert record.status_code == 404
    assert application.state.request_metrics.snapshot()[
        ("GET", "unmatched", 404)
    ] == 1
    prometheus_metrics = application.state.request_metrics.render_prometheus()
    assert 'watch_ai_http_requests_total{method="GET",route="unmatched",status="404"} 1' in (
        prometheus_metrics
    )
    assert "watch_ai_http_request_duration_seconds_sum" in prometheus_metrics


def test_invalid_correlation_header_is_replaced_with_a_generated_uuid() -> None:
    application = create_app(app_env="test")
    with TestClient(application) as client:
        response = client.get(
            "/health",
            headers={"X-Correlation-ID": "x" * 200},
        )

    generated = response.headers["X-Correlation-ID"]
    assert generated != "x" * 200
    assert len(generated) == 36


def test_monthly_model_budget_tracks_actual_cost_and_reports_overage() -> None:
    budget = MonthlyModelBudget(monthly_limit_usd=Decimal("0.010"))
    now = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)

    first_exceeded = budget.record_usage("vision/test", Decimal("0.004"), at=now)
    second_exceeded = budget.record_usage("vision/test", Decimal("0.007"), at=now)
    snapshot = budget.snapshot(at=now)

    assert first_exceeded is False
    assert second_exceeded is True
    assert snapshot.spent_usd == Decimal("0.011")
    assert snapshot.remaining_usd == Decimal("0")


def test_monthly_model_budget_is_durable_across_adapter_instances() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[ModelUsageRecord.__table__])
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    now = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
    budget = SqlAlchemyMonthlyModelBudget(sessions, Decimal("0.010"))
    budget.record_usage("vision/test", Decimal("0.006"), at=now)

    restarted_budget = SqlAlchemyMonthlyModelBudget(sessions, Decimal("0.010"))
    assert restarted_budget.snapshot(at=now).spent_usd == Decimal("0.006")
    assert restarted_budget.record_usage("vision/test", Decimal("0.005"), at=now)
    assert restarted_budget.is_over_budget(at=now)
    engine.dispose()


def test_openrouter_usage_cost_is_recorded_without_logging_image_or_key(caplog) -> None:
    budget = MonthlyModelBudget(monthly_limit_usd=Decimal("1.00"))
    answer = {
        "statement": "Derive f(x) = x^2.",
        "problem_type": "derivative",
        "confidence": "high",
        "needs_review": False,
    }
    private_image_marker = "private-jpeg-marker"

    def respond(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(answer)}}],
                "usage": {"cost": "0.0042"},
            },
        )

    client = httpx.Client(
        base_url="https://openrouter.ai/api/v1",
        transport=httpx.MockTransport(respond),
    )
    provider = OpenRouterVisionProvider(
        api_key="server-only-test-key",
        model="vision/test",
        client=client,
        usage_recorder=budget,
    )
    message = InboundMessage(
        provider_message_id="telemetry-test-message",
        sender_hmac="private-sender-hmac",
    )

    result = provider.interpret(message, image_bytes=private_image_marker.encode())
    snapshot = budget.snapshot()
    provider.close()

    assert result.statement == answer["statement"]
    assert snapshot.spent_usd == Decimal("0.0042")
    assert private_image_marker not in caplog.text
    assert "server-only-test-key" not in caplog.text
