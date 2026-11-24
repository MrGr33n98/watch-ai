"""Interpret an admitted image and persist only mathematically safe solutions."""

from __future__ import annotations

from typing import Protocol

from app.application.ports import VisionProvider
from app.application.solution_policy import SolutionPolicy
from app.domain.ingestion.models import InboundMessage
from app.domain.interpretation.models import InterpretedExercise
from app.domain.math_verification.solution import (
    SolutionProblem,
    SolutionStatus,
    SolutionStep,
    SolutionStepKind,
    SolvedExercise,
)


class SolutionProblemMapper(Protocol):
    def to_problem(self, exercise: InterpretedExercise, ordinal: int) -> SolutionProblem: ...


class SolutionResultRepository(Protocol):
    def save_solution(
        self,
        message: InboundMessage,
        exercise: InterpretedExercise,
        result: SolvedExercise,
    ) -> None: ...


class SolutionPipeline:
    def __init__(
        self,
        *,
        vision_provider: VisionProvider,
        problem_mapper: SolutionProblemMapper,
        solution_policy: SolutionPolicy,
        result_repository: SolutionResultRepository,
    ) -> None:
        self._vision_provider = vision_provider
        self._problem_mapper = problem_mapper
        self._solution_policy = solution_policy
        self._result_repository = result_repository

    def process(self, message: InboundMessage, *, image_bytes: bytes) -> SolvedExercise:
        if message.question_ordinal is None:
            raise ValueError("Inbound photo has no ordered question association")
        exercise = self._vision_provider.interpret(message, image_bytes=image_bytes)
        if (
            exercise.needs_review
            or exercise.statement is None
            or exercise.problem_type is None
            or exercise.confidence.value != "high"
        ):
            result = self._review(message.question_ordinal, exercise.statement)
        else:
            try:
                problem = self._problem_mapper.to_problem(exercise, message.question_ordinal)
                result = self._solution_policy.solve(problem)
            except (TypeError, ValueError):
                result = self._review(message.question_ordinal, exercise.statement)

        self._result_repository.save_solution(message, exercise, result)
        return result

    @staticmethod
    def _review(ordinal: int, statement: str | None) -> SolvedExercise:
        visible_statement = statement or "A imagem precisa ser revisada antes da interpretação."
        return SolvedExercise(
            ordinal=ordinal,
            status=SolutionStatus.NEEDS_REVIEW,
            verification_status="inconclusive",
            verified=False,
            final_answer=None,
            units=None,
            review_reason="interpretation_ambiguous",
            steps=(
                SolutionStep(
                    ordinal=1,
                    kind=SolutionStepKind.STATEMENT,
                    title="Enunciado",
                    plain_text=visible_statement,
                    alt_text=visible_statement,
                    verified=False,
                ),
                SolutionStep(
                    ordinal=2,
                    kind=SolutionStepKind.VERIFICATION,
                    title="Revisão necessária",
                    plain_text="Não há resultado verificado para esta questão.",
                    alt_text="A questão precisa ser revisada antes de exibir um resultado.",
                    verified=False,
                ),
            ),
        )
