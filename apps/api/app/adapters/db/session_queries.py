from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.adapters.db.models import QuestionRecord, StudySessionRecord
from app.application.session_queries import (
    QuestionDetailRead,
    QuestionSummaryRead,
    SessionSummaryRead,
    SolutionStepRead,
    StudySessionRead,
)


class SqlAlchemySessionQueryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_sessions(self, owner_id: UUID, limit: int) -> Sequence[SessionSummaryRead]:
        sessions = self._session.scalars(
            select(StudySessionRecord)
            .where(StudySessionRecord.user_id == owner_id)
            .order_by(StudySessionRecord.created_at.desc(), StudySessionRecord.id.desc())
            .limit(limit)
        ).all()
        return tuple(self._to_summary(session) for session in sessions)

    def get_session(self, owner_id: UUID, session_id: UUID) -> StudySessionRead | None:
        statement = (
            select(StudySessionRecord)
            .options(joinedload(StudySessionRecord.questions))
            .where(
                StudySessionRecord.id == session_id,
                StudySessionRecord.user_id == owner_id,
            )
        )
        study_session = self._session.execute(statement).unique().scalar_one_or_none()
        if study_session is None:
            return None
        summary = self._to_summary(study_session)
        return StudySessionRead(
            id=summary.id,
            status=summary.status,
            received_count=summary.received_count,
            expected_count=summary.expected_count,
            created_at=summary.created_at,
            questions=tuple(
                self._to_question_summary(question)
                for question in sorted(study_session.questions, key=lambda item: item.ordinal)
            ),
        )

    def get_question(
        self,
        owner_id: UUID,
        session_id: UUID,
        ordinal: int,
    ) -> QuestionDetailRead | None:
        question = self._session.scalar(
            select(QuestionRecord)
            .options(selectinload(QuestionRecord.steps))
            .join(StudySessionRecord, QuestionRecord.session_id == StudySessionRecord.id)
            .where(
                QuestionRecord.session_id == session_id,
                QuestionRecord.ordinal == ordinal,
                StudySessionRecord.user_id == owner_id,
            )
        )
        if question is None:
            return None
        summary = self._to_question_summary(question)
        all_steps = tuple(
            SolutionStepRead(
                ordinal=step.ordinal,
                kind=step.kind,
                title=step.title,
                plain_text=step.plain_text,
                latex=step.latex,
                render_url=step.render_url,
                alt_text=step.alt_text,
                verified=step.verified,
            )
            for step in sorted(question.steps, key=lambda item: item.ordinal)
        )
        verified = (
            question.status == "ready"
            and question.verification_status == "verified"
            and question.final_answer is not None
            and any(step.kind == "calculation" and step.verified for step in all_steps)
            and any(step.kind == "verification" and step.verified for step in all_steps)
            and any(step.kind == "result" and step.verified for step in all_steps)
        )
        steps = all_steps
        verification_status = question.verification_status
        if verification_status == "verified" and not verified:
            verification_status = "unverified"
        return QuestionDetailRead(
            id=summary.id,
            ordinal=summary.ordinal,
            status=summary.status,
            title=summary.title,
            result_preview=summary.result_preview,
            statement=question.statement_text or "",
            verified=verified,
            verification_status=verification_status,
            final_answer=question.final_answer,
            units=question.units,
            steps=steps,
        )

    @staticmethod
    def _to_summary(study_session: StudySessionRecord) -> SessionSummaryRead:
        return SessionSummaryRead(
            id=study_session.id,
            status=study_session.status,
            received_count=study_session.received_count,
            expected_count=study_session.expected_count,
            created_at=study_session.created_at,
        )

    @staticmethod
    def _to_question_summary(question: QuestionRecord) -> QuestionSummaryRead:
        preview = None
        if question.status == "ready" and question.final_answer is not None:
            preview = " ".join(part for part in (question.final_answer, question.units) if part)
        return QuestionSummaryRead(
            id=question.id,
            ordinal=question.ordinal,
            status=question.status,
            title=question.problem_type,
            result_preview=preview,
        )
