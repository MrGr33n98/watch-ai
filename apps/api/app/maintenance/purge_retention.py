"""Run configured media/session retention once; schedule only after policy approval."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.db.retention import SqlAlchemySessionRetentionRepository
from app.adapters.storage.private_media import PrivateMediaStore
from app.application.retention import RetentionRun, SessionRetentionPolicy, SessionRetentionService


def run_retention_pass() -> RetentionRun:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required to run retention")

    policy = SessionRetentionPolicy.from_environment()
    media_directory = Path(os.getenv("WATCH_AI_MEDIA_DIR", ".watch-ai-private-media"))
    engine = create_engine(database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    totals = RetentionRun(deleted_sessions=0, purged_media=0)
    try:
        while True:
            with session_factory() as session:
                result = _run_batch(session, media_directory, policy)
            totals = RetentionRun(
                deleted_sessions=totals.deleted_sessions + result.deleted_sessions,
                purged_media=totals.purged_media + result.purged_media,
            )
            if result.deleted_sessions == 0 and result.purged_media == 0:
                return totals
    finally:
        engine.dispose()


def _run_batch(
    session: Session,
    media_directory: Path,
    policy: SessionRetentionPolicy,
) -> RetentionRun:
    return SessionRetentionService(
        SqlAlchemySessionRetentionRepository(session),
        PrivateMediaStore(media_directory),
        policy,
    ).purge_expired()


if __name__ == "__main__":
    result = run_retention_pass()
    print(
        "retention complete: "
        f"deleted_sessions={result.deleted_sessions} purged_media={result.purged_media}"
    )
