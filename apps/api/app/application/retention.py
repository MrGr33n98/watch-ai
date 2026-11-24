"""Owner-authorized deletion and configurable expiry for study-session data."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SessionDeletionBatch:
    session_ids: tuple[UUID, ...] = ()
    media_shas_to_purge: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RetentionRun:
    deleted_sessions: int
    purged_media: int


class SessionRetentionRepository(Protocol):
    def delete_owned_session(
        self,
        owner_id: UUID,
        session_id: UUID,
    ) -> SessionDeletionBatch | None: ...

    def delete_expired_media(self, cutoff: datetime, *, limit: int) -> SessionDeletionBatch: ...

    def mark_media_purged(self, media_shas: tuple[str, ...], *, cutoff: datetime) -> None: ...

    def delete_expired_sessions(
        self,
        cutoff: datetime,
        *,
        limit: int,
    ) -> SessionDeletionBatch: ...


class MediaPurger(Protocol):
    def delete(self, media_sha: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class SessionRetentionPolicy:
    media_retention_hours: int = 24
    session_retention_days: int = 30
    batch_size: int = 100

    def __post_init__(self) -> None:
        if isinstance(self.media_retention_hours, bool) or not (
            1 <= self.media_retention_hours <= 87600
        ):
            raise ValueError("Media retention must be between 1 and 87600 hours")
        if isinstance(self.session_retention_days, bool) or not (
            1 <= self.session_retention_days <= 3650
        ):
            raise ValueError("Session retention must be between 1 and 3650 days")
        if isinstance(self.batch_size, bool) or not 1 <= self.batch_size <= 1000:
            raise ValueError("Retention batch size must be between 1 and 1000")

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> SessionRetentionPolicy:
        source = os.environ if environment is None else environment
        raw_hours = source.get("MEDIA_RETENTION_HOURS", "24").strip()
        raw_days = source.get("SESSION_RETENTION_DAYS", "30").strip()
        try:
            media_retention_hours = int(raw_hours)
            session_retention_days = int(raw_days)
        except ValueError as error:
            raise ValueError("Media and session retention values must be integers") from error
        return cls(
            media_retention_hours=media_retention_hours,
            session_retention_days=session_retention_days,
        )

    def media_cutoff(self, now: datetime | None = None) -> datetime:
        instant = now or datetime.now(UTC)
        if instant.utcoffset() is None:
            raise ValueError("Retention cutoff requires a timezone-aware timestamp")
        return instant - timedelta(hours=self.media_retention_hours)

    def session_cutoff(self, now: datetime | None = None) -> datetime:
        instant = now or datetime.now(UTC)
        if instant.utcoffset() is None:
            raise ValueError("Retention cutoff requires a timezone-aware timestamp")
        return instant - timedelta(days=self.session_retention_days)


class SessionRetentionService:
    def __init__(
        self,
        repository: SessionRetentionRepository,
        media_purger: MediaPurger,
        policy: SessionRetentionPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._media_purger = media_purger
        self._policy = policy or SessionRetentionPolicy()

    def delete_session(self, owner_id: UUID, session_id: UUID) -> bool:
        batch = self._repository.delete_owned_session(owner_id, session_id)
        if batch is None:
            return False
        self._purge_media(batch.media_shas_to_purge)
        return True

    def purge_expired(self, *, now: datetime | None = None) -> RetentionRun:
        expired_media = self._repository.delete_expired_media(
            self._policy.media_cutoff(now),
            limit=self._policy.batch_size,
        )
        media_shas = tuple(sorted(set(expired_media.media_shas_to_purge)))
        if media_shas:
            self._purge_media(media_shas)
            self._repository.mark_media_purged(
                media_shas,
                cutoff=self._policy.media_cutoff(now),
            )
        expired_sessions = self._repository.delete_expired_sessions(
            self._policy.session_cutoff(now),
            limit=self._policy.batch_size,
        )
        expired_session_media = tuple(sorted(set(expired_sessions.media_shas_to_purge)))
        session_media_count = self._purge_media(expired_session_media)
        return RetentionRun(
            len(expired_sessions.session_ids),
            len(media_shas) + session_media_count,
        )

    def _purge_media(self, media_shas: tuple[str, ...]) -> int:
        unique_shas = set(media_shas)
        for media_sha in unique_shas:
            self._media_purger.delete(media_sha)
        return len(unique_shas)
