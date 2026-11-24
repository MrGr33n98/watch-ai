"""Persist verified question solutions and their ordered presentation steps."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.db.models import QuestionRecord, SolutionStepRecord, StudySessionRecord
from app.domain.ingestion.models import InboundMessage
from app.domain.interpretation.models import InterpretedExercise
from app.domain.math_verification.solution import (
    SolutionStatus,
    SolutionStepKind,
    SolvedExercise,
)


class SqlAlchemySolutionRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save_solution(
        self,
        message: InboundMessage,
        exercise: InterpretedExercise,
        result: SolvedExercise,
    ) -> None:
        if message.session_id is None or message.question_ordinal is None:
            raise ValueError("Cannot save a solution without its session and question ordinal")

        with self._session_factory() as session, session.begin():
            study_session = session.scalar(
                select(StudySessionRecord)
                .where(StudySessionRecord.id == message.session_id)
                .with_for_update()
            )
            question = session.scalar(
                select(QuestionRecord)
                .where(
                    QuestionRecord.session_id == message.session_id,
                    QuestionRecord.ordinal == message.question_ordinal,
                )
                .with_for_update()
            )
            if study_session is None or question is None:
                raise LookupError("Inbound photo has no persisted study question")

            verified = _has_complete_verification(result)
            question.statement_text = exercise.statement
            question.problem_type = exercise.problem_type
            question.confidence = exercise.confidence.value
            question.status = (
                SolutionStatus.READY.value if verified else SolutionStatus.NEEDS_REVIEW.value
            )
            question.verification_status = "verified" if verified else "inconclusive"
            question.final_answer = result.final_answer if verified else None
            question.units = result.units if verified else None

            existing_steps = session.scalars(
                select(SolutionStepRecord).where(SolutionStepRecord.question_id == question.id)
            ).all()
            for step in existing_steps:
                session.delete(step)
            session.flush()
            for domain_step in result.steps:
                if not verified and domain_step.kind in {
                    SolutionStepKind.CALCULATION,
                    SolutionStepKind.RESULT,
                }:
                    continue
                session.add(
                    SolutionStepRecord(
                        id=uuid4(),
                        question_id=question.id,
                        ordinal=domain_step.ordinal,
                        kind=domain_step.kind.value,
                        title=domain_step.title,
                        plain_text=domain_step.plain_text,
                        latex=domain_step.latex,
                        alt_text=domain_step.alt_text,
                        verified=domain_step.verified if verified else False,
                    )
                )

            session.flush()
            question_statuses = session.scalars(
                select(QuestionRecord.status).where(
                    QuestionRecord.session_id == study_session.id
                )
            ).all()
            if all(status in {"ready", "needs_review", "failed"} for status in question_statuses):
                if "needs_review" in question_statuses:
                    study_session.status = "needs_review"
                elif all(status == "ready" for status in question_statuses):
                    study_session.status = (
                        "ready"
                        if len(question_statuses) == study_session.expected_count
                        else "partial"
                    )
                elif all(status == "failed" for status in question_statuses):
                    study_session.status = "failed"
                else:
                    study_session.status = "partial"
                study_session.completed_at = datetime.now(UTC)
            else:
                study_session.status = "processing"


def _has_complete_verification(result: SolvedExercise) -> bool:
    if (
        result.status is not SolutionStatus.READY
        or not result.verified
        or result.verification_status != "verified"
        or result.final_answer is None
    ):
        return False
    return all(
        any(step.kind is kind and step.verified for step in result.steps)
        for kind in (
            SolutionStepKind.CALCULATION,
            SolutionStepKind.VERIFICATION,
            SolutionStepKind.RESULT,
        )
    )
