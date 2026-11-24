"""SQL persistence for owner-scoped deletion and retention expiry."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, exists, func, or_, select, update
from sqlalchemy.orm import Session, aliased

from app.adapters.db.models import (
    InboundMessageRecord,
    OutboxEventRecord,
    QuestionRecord,
    SenderSessionBindingRecord,
    SolutionStepRecord,
    StudySessionRecord,
)
from app.application.retention import SessionDeletionBatch


class SqlAlchemySessionRetentionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def delete_owned_session(self, owner_id: UUID, session_id: UUID) -> SessionDeletionBatch | None:
        owned_id = self._session.scalar(
            select(StudySessionRecord.id)
            .where(
                StudySessionRecord.id == session_id,
                StudySessionRecord.user_id == owner_id,
            )
            .with_for_update()
        )
        if owned_id is None:
            return None
        batch = self._delete_session_ids((owned_id,))
        self._session.commit()
        return batch

    def delete_expired_sessions(
        self,
        cutoff: datetime,
        *,
        limit: int,
    ) -> SessionDeletionBatch:
        session_ids = tuple(
            self._session.scalars(
                select(StudySessionRecord.id)
                .where(
                    func.coalesce(
                        StudySessionRecord.completed_at,
                        StudySessionRecord.created_at,
                    )
                    < cutoff
                )
                .order_by(
                    func.coalesce(
                        StudySessionRecord.completed_at,
                        StudySessionRecord.created_at,
                    ),
                    StudySessionRecord.id,
                )
                .limit(limit)
                .with_for_update(skip_locked=True)
            ).all()
        )
        if not session_ids:
            return SessionDeletionBatch()
        batch = self._delete_session_ids(session_ids)
        self._session.commit()
        return batch

    def delete_expired_media(self, cutoff: datetime, *, limit: int) -> SessionDeletionBatch:
        terminal_statuses = ("ready", "needs_review", "failed")
        candidate_question = aliased(QuestionRecord)
        active_question = aliased(QuestionRecord)
        candidate_shas = {
            media_sha
            for _, media_sha in self._session.execute(
                select(candidate_question.id, candidate_question.media_sha)
                .join(
                    StudySessionRecord,
                    candidate_question.session_id == StudySessionRecord.id,
                )
                .where(
                    candidate_question.media_sha.is_not(None),
                    candidate_question.status.in_(terminal_statuses),
                    candidate_question.updated_at < cutoff,
                    ~exists(
                        select(active_question.id).where(
                            active_question.media_sha == candidate_question.media_sha,
                            or_(
                                active_question.status.not_in(terminal_statuses),
                                active_question.updated_at >= cutoff,
                            ),
                        )
                    ),
                    ~exists(
                        select(InboundMessageRecord.id).where(
                            InboundMessageRecord.media_sha == candidate_question.media_sha,
                            InboundMessageRecord.state.in_(
                                ("received", "queued", "processing")
                            ),
                        )
                    ),
                )
                .order_by(candidate_question.updated_at, candidate_question.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            ).all()
            if media_sha is not None
        }
        return SessionDeletionBatch(
            media_shas_to_purge=tuple(sorted(candidate_shas))
        )

    def mark_media_purged(self, media_shas: tuple[str, ...], *, cutoff: datetime) -> None:
        if media_shas:
            self._session.execute(
                update(QuestionRecord)
                .where(
                    QuestionRecord.media_sha.in_(media_shas),
                    QuestionRecord.status.in_(("ready", "needs_review", "failed")),
                    QuestionRecord.updated_at < cutoff,
                )
                .values(media_sha=None)
            )
        self._session.commit()

    def _delete_session_ids(self, session_ids: tuple[UUID, ...]) -> SessionDeletionBatch:
        question_ids = tuple(
            self._session.scalars(
                select(QuestionRecord.id).where(QuestionRecord.session_id.in_(session_ids))
            ).all()
        )
        media_shas = {
            media_sha
            for media_sha in self._session.scalars(
                select(QuestionRecord.media_sha).where(
                    QuestionRecord.session_id.in_(session_ids),
                    QuestionRecord.media_sha.is_not(None),
                )
            ).all()
            if media_sha is not None
        }
        message_ids = tuple(
            self._session.scalars(
                select(InboundMessageRecord.id).where(
                    InboundMessageRecord.session_id.in_(session_ids)
                )
            ).all()
        )
        if message_ids:
            self._session.execute(
                delete(OutboxEventRecord).where(
                    OutboxEventRecord.aggregate_type == "inbound_message",
                    OutboxEventRecord.aggregate_id.in_(message_ids),
                )
            )
            self._session.execute(
                update(InboundMessageRecord)
                .where(InboundMessageRecord.id.in_(message_ids))
                .values(
                    session_id=None,
                    question_ordinal=None,
                    media_sha=None,
                    state="rejected",
                )
            )
        self._session.execute(
            delete(SenderSessionBindingRecord).where(
                SenderSessionBindingRecord.session_id.in_(session_ids)
            )
        )
        if question_ids:
            self._session.execute(
                delete(SolutionStepRecord).where(SolutionStepRecord.question_id.in_(question_ids))
            )
            self._session.execute(
                delete(QuestionRecord).where(QuestionRecord.id.in_(question_ids))
            )
        self._session.execute(
            delete(StudySessionRecord).where(StudySessionRecord.id.in_(session_ids))
        )
        referenced_question_shas = {
            media_sha
            for media_sha in self._session.scalars(
                select(QuestionRecord.media_sha).where(
                    QuestionRecord.media_sha.in_(media_shas),
                )
            ).all()
            if media_sha is not None
        }
        referenced_inbound_shas = {
            media_sha
            for media_sha in self._session.scalars(
                select(InboundMessageRecord.media_sha).where(
                    InboundMessageRecord.media_sha.in_(media_shas),
                )
            ).all()
            if media_sha is not None
        }
        return SessionDeletionBatch(
            session_ids=session_ids,
            media_shas_to_purge=tuple(
                sorted(media_shas - referenced_question_shas - referenced_inbound_shas)
            ),
        )
