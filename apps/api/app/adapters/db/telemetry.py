"""PostgreSQL-backed model usage accounting."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.db.models import ModelUsageRecord
from app.infrastructure.telemetry import BudgetSnapshot


class SqlAlchemyMonthlyModelBudget:
    """Persist provider-reported costs and aggregate them by UTC calendar month."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        monthly_limit_usd: Decimal | None,
    ) -> None:
        if monthly_limit_usd is not None and (
            not monthly_limit_usd.is_finite() or monthly_limit_usd <= 0
        ):
            raise ValueError("Monthly model budget must be a positive finite amount")
        self._session_factory = session_factory
        self._limit = monthly_limit_usd

    def is_over_budget(self, *, at: datetime | None = None) -> bool:
        return self.snapshot(at=at).exceeded

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
        instant = _utc_datetime(at)
        with self._session_factory.begin() as database:
            database.add(
                ModelUsageRecord(
                    model=normalized_model,
                    cost_usd=cost_usd,
                    recorded_at=instant,
                )
            )
        return self.snapshot(at=instant).exceeded

    def snapshot(self, *, at: datetime | None = None) -> BudgetSnapshot:
        instant = _utc_datetime(at)
        month_start = instant.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)
        with self._session_factory() as database:
            raw_spend = database.scalar(
                select(func.coalesce(func.sum(ModelUsageRecord.cost_usd), 0)).where(
                    ModelUsageRecord.recorded_at >= month_start,
                    ModelUsageRecord.recorded_at < month_end,
                )
            )
        spent = Decimal(str(cast(object, raw_spend)))
        remaining = None if self._limit is None else max(Decimal("0"), self._limit - spent)
        return BudgetSnapshot(
            month=month_start.strftime("%Y-%m"),
            spent_usd=spent,
            limit_usd=self._limit,
            remaining_usd=remaining,
            exceeded=self._limit is not None and spent >= self._limit,
        )


def _utc_datetime(value: datetime | None) -> datetime:
    instant = value or datetime.now(UTC)
    if instant.utcoffset() is None:
        raise ValueError("Model usage timestamp must be timezone-aware")
    return instant.astimezone(UTC)
