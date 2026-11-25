"""Structured audit adapter that never serializes message payloads or exceptions."""

from __future__ import annotations

import logging


class StructuredOutboxAudit:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("watch_ai.outbox")

    def record(
        self,
        *,
        event_type: str,
        outcome: str,
        attempt_count: int,
        error_code: str | None,
    ) -> None:
        self._logger.info(
            "outbox delivery",
            extra={
                "event_type": event_type,
                "outcome": outcome,
                "attempt_count": attempt_count,
                "error_code": error_code,
            },
        )
