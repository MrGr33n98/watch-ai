"""Redacted request telemetry and monthly multimodal usage accounting."""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_HTTP_LOGGER = logging.getLogger("watch_ai.http")


class ModelUsageRecorder(Protocol):
    def is_over_budget(self, *, at: datetime | None = None) -> bool: ...

    def record_usage(
        self,
        model: str,
        cost_usd: Decimal,
        *,
        at: datetime | None = None,
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class BudgetSnapshot:
    month: str
    spent_usd: Decimal
    limit_usd: Decimal | None
    remaining_usd: Decimal | None
    exceeded: bool


class MonthlyModelBudget:
    """Thread-safe process ledger; production persistence is provided by the SQL adapter."""

    def __init__(self, monthly_limit_usd: Decimal | None) -> None:
        if monthly_limit_usd is not None and (
            not monthly_limit_usd.is_finite() or monthly_limit_usd <= 0
        ):
            raise ValueError("Monthly model budget must be a positive finite amount")
        self._limit = monthly_limit_usd
        self._lock = threading.Lock()
        self._spend: dict[tuple[str, str], Decimal] = defaultdict(Decimal)

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> MonthlyModelBudget:
        source = os.environ if environment is None else environment
        raw_limit = source.get("MONTHLY_MODEL_BUDGET_USD", "").strip()
        if not raw_limit:
            return cls(None)
        try:
            limit = Decimal(raw_limit)
        except Exception as error:
            raise ValueError("MONTHLY_MODEL_BUDGET_USD must be a decimal amount") from error
        return cls(limit)

    def is_over_budget(self, *, at: datetime | None = None) -> bool:
        snapshot = self.snapshot(at=at)
        return snapshot.exceeded

    def record_usage(
        self,
        model: str,
        cost_usd: Decimal,
        *,
        at: datetime | None = None,
    ) -> bool:
        normalized_model = model.strip()
        if not normalized_model:
            raise ValueError("Model name must not be empty")
        if not cost_usd.is_finite() or cost_usd < 0:
            raise ValueError("Model usage cost must be finite and non-negative")
        instant = at or datetime.now(UTC)
        if instant.utcoffset() is None:
            raise ValueError("Model usage timestamp must be timezone-aware")
        month = instant.astimezone(UTC).strftime("%Y-%m")
        with self._lock:
            key = (month, normalized_model)
            self._spend[key] += cost_usd
            spent = sum(
                (
                    value
                    for (recorded_month, _), value in self._spend.items()
                    if recorded_month == month
                ),
                Decimal("0"),
            )
        return self._limit is not None and spent >= self._limit

    def snapshot(self, *, at: datetime | None = None) -> BudgetSnapshot:
        instant = at or datetime.now(UTC)
        if instant.utcoffset() is None:
            raise ValueError("Budget snapshot timestamp must be timezone-aware")
        month = instant.astimezone(UTC).strftime("%Y-%m")
        with self._lock:
            spent = sum(
                (
                    value
                    for (recorded_month, _), value in self._spend.items()
                    if recorded_month == month
                ),
                Decimal("0"),
            )
        remaining = None if self._limit is None else max(Decimal("0"), self._limit - spent)
        return BudgetSnapshot(
            month=month,
            spent_usd=spent,
            limit_usd=self._limit,
            remaining_usd=remaining,
            exceeded=self._limit is not None and spent >= self._limit,
        )


@dataclass(frozen=True, slots=True)
class RequestMetric:
    method: str
    route: str
    status_code: int
    count: int
    total_duration_seconds: float


class RequestMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: dict[tuple[str, str, int], tuple[int, float]] = {}

    def record(self, method: str, route: str, status_code: int, duration_seconds: float) -> None:
        key = (method, route, status_code)
        with self._lock:
            count, duration = self._values.get(key, (0, 0.0))
            self._values[key] = (count + 1, duration + max(0.0, duration_seconds))

    def snapshot(self) -> dict[tuple[str, str, int], int]:
        with self._lock:
            return {key: count for key, (count, _) in self._values.items()}

    def render_prometheus(self) -> str:
        with self._lock:
            values = tuple(self._values.items())
        lines: list[str] = []
        for (method, route, status_code), (count, duration) in sorted(values):
            labels = (
                f'method="{_escape_label(method)}",route="{_escape_label(route)}",'
                f'status="{status_code}"'
            )
            lines.append(f"watch_ai_http_requests_total{{{labels}}} {count}")
            lines.append(f"watch_ai_http_request_duration_seconds_sum{{{labels}}} {duration:.6f}")
        return "\n".join(lines) + ("\n" if lines else "")


class RequestTelemetryMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, metrics: RequestMetrics) -> None:
        super().__init__(app)
        self._metrics = metrics

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        supplied_id = request.headers.get("X-Correlation-ID", "")
        correlation_id = (
            supplied_id if _CORRELATION_ID_PATTERN.fullmatch(supplied_id) else str(uuid4())
        )
        request.state.correlation_id = correlation_id
        started = time.perf_counter()
        status_code = 500
        response: Response | None = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            duration = max(0.0, time.perf_counter() - started)
            route_object = request.scope.get("route")
            route = getattr(route_object, "path", "unmatched")
            if not isinstance(route, str):
                route = "unmatched"
            self._metrics.record(request.method, route, status_code, duration)
            _HTTP_LOGGER.info(
                "http_request",
                extra={
                    "event": "http_request",
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "route": route,
                    "status_code": status_code,
                    "duration_ms": round(duration * 1000, 3),
                },
            )


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
