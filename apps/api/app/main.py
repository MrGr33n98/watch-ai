import os
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.adapters.db.batches import SqlAlchemyBatchRepository
from app.adapters.db.ingestion import SqlAlchemyUnitOfWorkFactory
from app.adapters.db.telemetry import SqlAlchemyMonthlyModelBudget
from app.adapters.http.admin import router as admin_router
from app.adapters.http.delivery import router as delivery_router
from app.adapters.http.health import router as health_router
from app.adapters.http.pairing_rate_limit import PairingRateLimiter
from app.adapters.http.phone_ui import router as phone_ui_router
from app.adapters.http.watch_api import router as watch_router
from app.adapters.openrouter.provider import OpenRouterVisionProvider
from app.adapters.renderer.formulas import PrivateFormulaAssetStore
from app.adapters.storage.private_media import PrivateMediaStore
from app.adapters.waha.media import WahaMediaDownloader
from app.adapters.waha.replies import WahaReplyClient
from app.adapters.waha.webhook import (
    InboundMessageIngestor,
    WahaBatchCoordinator,
    WahaJpegDownloader,
    WahaTextReplier,
    WahaWebhookSettings,
)
from app.adapters.waha.webhook import (
    router as waha_router,
)
from app.application.batches import BatchSessionService
from app.application.ingestion import IngestInboundMessage
from app.application.ports import AdmittedMediaStorage, UnitOfWorkFactory
from app.application.retention import SessionRetentionPolicy
from app.infrastructure.telemetry import (
    ModelUsageRecorder,
    MonthlyModelBudget,
    RequestMetrics,
    RequestTelemetryMiddleware,
)
from app.worker import OutboxWorkerService, build_worker_from_environment


def create_app(
    app_env: str | None = None,
    *,
    session_factory: sessionmaker[Session] | None = None,
    waha_settings: WahaWebhookSettings | None = None,
    waha_ingestion: InboundMessageIngestor | None = None,
    waha_batch_service: WahaBatchCoordinator | None = None,
    waha_media_downloader: WahaJpegDownloader | None = None,
    waha_media_store: AdmittedMediaStorage | None = None,
    waha_reply_client: WahaTextReplier | None = None,
    formula_asset_store: PrivateFormulaAssetStore | None = None,
    admin_api_key: str | None = None,
) -> FastAPI:
    environment = app_env
    if environment is None:
        environment = os.getenv("APP_ENV") or "production"
    environment = environment.strip().lower()
    engine: Engine | None = None
    configured_session_factory = session_factory
    if configured_session_factory is None and (database_url := os.getenv("DATABASE_URL")):
        engine = create_engine(database_url, pool_pre_ping=True)
        configured_session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    configured_waha_settings = waha_settings or WahaWebhookSettings.from_environment()
    configured_waha_ingestion = waha_ingestion
    if configured_waha_ingestion is None and configured_session_factory is not None:
        configured_waha_ingestion = IngestInboundMessage(
            cast(
                UnitOfWorkFactory,
                SqlAlchemyUnitOfWorkFactory(configured_session_factory),
            )
        )
    configured_waha_batch_service = waha_batch_service
    if configured_waha_batch_service is None and configured_session_factory is not None:
        configured_waha_batch_service = BatchSessionService(
            SqlAlchemyBatchRepository(configured_session_factory),
            expiry=timedelta(seconds=configured_waha_settings.batch_expiry_seconds),
        )
    configured_waha_media_downloader = waha_media_downloader
    configured_waha_media_store = waha_media_store
    if configured_waha_media_store is None:
        configured_waha_media_store = PrivateMediaStore(
            configured_waha_settings.media_storage_directory
        )
    configured_waha_reply_client = waha_reply_client
    if configured_waha_settings.enabled and configured_waha_settings.ready:
        if configured_waha_media_downloader is None:
            configured_waha_media_downloader = WahaMediaDownloader(
                base_url=configured_waha_settings.media_base_url,
                api_key=configured_waha_settings.media_api_key,
            )
        if configured_waha_settings.send_replies and configured_waha_reply_client is None:
            configured_waha_reply_client = WahaReplyClient(
                base_url=configured_waha_settings.media_base_url,
                api_key=configured_waha_settings.media_api_key,
            )
    configured_admin_key = (
        os.getenv("ADMIN_API_KEY", "") if admin_api_key is None else admin_api_key
    ).strip()

    configured_formula_asset_store = formula_asset_store or PrivateFormulaAssetStore(
        Path(os.getenv("WATCH_AI_RENDER_DIR", ".watch-ai-private-renders"))
    )
    embedded_worker_enabled = (
        os.getenv("ENABLE_EMBEDDED_WORKER", "false").strip().lower() in {"true", "1", "yes"}
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        worker: OutboxWorkerService | None = None
        worker_thread: threading.Thread | None = None
        if embedded_worker_enabled and configured_session_factory is not None:
            worker = build_worker_from_environment(configured_session_factory)
            application.state.embedded_worker = worker
            worker_thread = threading.Thread(
                target=worker.run_forever,
                name="watch-ai-outbox-worker",
                daemon=True,
            )
            worker_thread.start()
        try:
            yield
        finally:
            if worker is not None:
                worker.stop()
            if worker_thread is not None:
                worker_thread.join(timeout=5)
            if engine is not None:
                engine.dispose()

    application = FastAPI(title="Watch AI API", version="0.1.0", lifespan=lifespan)
    request_metrics = RequestMetrics()
    application.state.session_factory = configured_session_factory
    application.state.pairing_rate_limiter = PairingRateLimiter()
    application.state.request_metrics = request_metrics
    monthly_budget = MonthlyModelBudget.from_environment()
    model_budget: ModelUsageRecorder
    if configured_session_factory is not None:
        model_budget = SqlAlchemyMonthlyModelBudget(
            configured_session_factory,
            monthly_budget.snapshot().limit_usd,
        )
    else:
        model_budget = monthly_budget
    application.state.model_budget = model_budget

    def build_openrouter_provider() -> OpenRouterVisionProvider:
        return OpenRouterVisionProvider.from_environment(usage_recorder=model_budget)

    application.state.openrouter_provider_factory = build_openrouter_provider
    application.state.waha_settings = configured_waha_settings
    application.state.waha_ingestion = configured_waha_ingestion
    application.state.waha_batch_service = configured_waha_batch_service
    application.state.waha_media_downloader = configured_waha_media_downloader
    application.state.waha_media_store = configured_waha_media_store
    application.state.waha_reply_client = configured_waha_reply_client
    application.state.admin_api_key = configured_admin_key
    application.state.formula_asset_store = configured_formula_asset_store
    application.state.embedded_worker = None
    application.state.session_retention_policy = SessionRetentionPolicy.from_environment()
    application.add_middleware(RequestTelemetryMiddleware, metrics=request_metrics)
    application.include_router(health_router)
    application.include_router(delivery_router)
    application.include_router(watch_router)
    application.include_router(waha_router)
    application.include_router(admin_router)
    application.include_router(phone_ui_router)

    @application.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request,
        exception: StarletteHTTPException,
    ) -> JSONResponse:
        error_codes = {
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            413: "upload_too_large",
            415: "unsupported_media_type",
            429: "rate_limited",
            503: "service_unavailable",
        }
        message = exception.detail if isinstance(exception.detail, str) else "Request failed"
        return JSONResponse(
            status_code=exception.status_code,
            content={
                "code": error_codes.get(exception.status_code, f"http_{exception.status_code}"),
                "message": message,
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
            headers=exception.headers,
        )

    if environment in {"development", "test"}:
        from app.adapters.http.dev_ingest import router as dev_ingest_router

        application.include_router(dev_ingest_router)

    return application


app = create_app()
