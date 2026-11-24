"""Background outbox worker draining inbound exercise photos to verified solutions."""

from __future__ import annotations

import logging
import os
import signal
import threading
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.db.ingestion import SqlAlchemyInboundMessageReader
from app.adapters.db.outbox_delivery import SqlAlchemyOutboxDeliveryRepository
from app.adapters.db.solutions import SqlAlchemySolutionRepository
from app.adapters.db.telemetry import SqlAlchemyMonthlyModelBudget
from app.adapters.openrouter.provider import OpenRouterVisionProvider
from app.adapters.queue.audit import StructuredOutboxAudit
from app.adapters.queue.fake_vision import FakeVisionProvider
from app.adapters.queue.inbound_handler import InboundMessageOutboxHandler
from app.adapters.renderer.formulas import FormulaRenderer, PrivateFormulaAssetStore
from app.adapters.storage.private_media import PrivateMediaStore
from app.application.outbox_dispatch import DispatchSummary, OutboxDispatcher, RetryPolicy
from app.application.ports import PrivateMediaReader, VisionProvider
from app.application.problem_mapper import StructuredProblemMapper
from app.application.solution_pipeline import SolutionPipeline
from app.application.solution_policy import SolutionPolicy
from app.infrastructure.telemetry import ModelUsageRecorder, MonthlyModelBudget

_WORKER_LOGGER = logging.getLogger("watch_ai.worker")


def build_vision_provider(
    *,
    environment: Mapping[str, str] | None = None,
    usage_recorder: ModelUsageRecorder | None = None,
) -> VisionProvider:
    source = os.environ if environment is None else environment
    app_env = source.get("APP_ENV", "production").strip().lower() or "production"
    selected = source.get("VISION_PROVIDER", "auto").strip().lower() or "auto"

    if selected == "fake":
        if app_env not in {"development", "test"}:
            raise RuntimeError("VISION_PROVIDER=fake is only allowed in development or test")
        return FakeVisionProvider()

    api_key = source.get("OPENROUTER_API_KEY", "").strip()
    model = source.get("OPENROUTER_MODEL", "").strip()
    if selected == "openrouter" or (api_key and model):
        if not api_key or not model:
            raise RuntimeError("OPENROUTER_API_KEY and OPENROUTER_MODEL are required")
        return OpenRouterVisionProvider(
            api_key=api_key,
            model=model,
            usage_recorder=usage_recorder,
        )

    raise RuntimeError(
        "Vision provider is not configured. Set OPENROUTER_API_KEY and OPENROUTER_MODEL, "
        "or VISION_PROVIDER=fake in development."
    )


class OutboxWorkerService:
    """Polls and dispatches due outbox jobs until stopped."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        media_reader: PrivateMediaReader,
        vision_provider: VisionProvider,
        formula_renderer: FormulaRenderer | None = None,
        retry_policy: RetryPolicy | None = None,
        poll_interval_seconds: float = 1.0,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("Worker poll interval must be positive")
        self._poll_interval_seconds = poll_interval_seconds
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        pipeline = SolutionPipeline(
            vision_provider=vision_provider,
            problem_mapper=StructuredProblemMapper(),
            solution_policy=SolutionPolicy(),
            result_repository=SqlAlchemySolutionRepository(session_factory),
            formula_renderer=formula_renderer,
        )
        handler = InboundMessageOutboxHandler(
            SqlAlchemyInboundMessageReader(session_factory),
            media_reader,
            pipeline,
        )
        self._dispatcher = OutboxDispatcher(
            SqlAlchemyOutboxDeliveryRepository(session_factory),
            handler,
            StructuredOutboxAudit(),
            policy=retry_policy or RetryPolicy(),
        )

    def run_once(self, *, now: datetime | None = None) -> DispatchSummary:
        return self._dispatcher.dispatch_once(now=now)

    def wake(self) -> None:
        self._wake_event.set()

    def stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()

    def run_forever(self) -> None:
        while not self._stop_event.is_set():
            try:
                summary = self.run_once()
            except Exception:
                _WORKER_LOGGER.exception("outbox_worker_iteration_failed")
                summary = DispatchSummary()
            if summary.claimed == 0:
                self._wake_event.wait(timeout=self._poll_interval_seconds)
                self._wake_event.clear()


def build_worker_from_environment(
    session_factory: sessionmaker[Session],
    *,
    environment: Mapping[str, str] | None = None,
) -> OutboxWorkerService:
    source = os.environ if environment is None else environment
    media_dir = Path(source.get("WATCH_AI_MEDIA_DIR", ".watch-ai-private-media"))
    render_dir = Path(source.get("WATCH_AI_RENDER_DIR", ".watch-ai-private-renders"))
    budget_config = MonthlyModelBudget.from_environment(source)
    budget_limit: Decimal | None = budget_config.snapshot().limit_usd
    usage_recorder = SqlAlchemyMonthlyModelBudget(session_factory, budget_limit)
    vision_provider = build_vision_provider(
        environment=source,
        usage_recorder=usage_recorder,
    )
    poll_interval = float(source.get("OUTBOX_POLL_INTERVAL_SECONDS", "1.0"))
    return OutboxWorkerService(
        session_factory=session_factory,
        media_reader=PrivateMediaStore(media_dir),
        vision_provider=vision_provider,
        formula_renderer=FormulaRenderer(PrivateFormulaAssetStore(render_dir)),
        poll_interval_seconds=poll_interval,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required to run the outbox worker")
    engine = create_engine(database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    worker = build_worker_from_environment(session_factory)

    def _handle_signal(_signum: int, _frame: object) -> None:
        worker.stop()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    _WORKER_LOGGER.info("outbox_worker_started")
    try:
        worker.run_forever()
    finally:
        engine.dispose()
        _WORKER_LOGGER.info("outbox_worker_stopped")


if __name__ == "__main__":
    main()
