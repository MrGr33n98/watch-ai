"""Map structured vision interpretations to typed verification inputs."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.domain.interpretation.models import ExtractedQuantity, InterpretedExercise
from app.domain.math_verification.quantities import PhysicalQuantity
from app.domain.math_verification.solution import ExerciseOperation, SolutionProblem

_OPERATION_ALIASES = {
    "fourier": ExerciseOperation.FOURIER,
    "fourier law": ExerciseOperation.FOURIER,
    "fourier_law": ExerciseOperation.FOURIER,
    "derivative": ExerciseOperation.DERIVATIVE,
    "derivada": ExerciseOperation.DERIVATIVE,
    "definite_integral": ExerciseOperation.DEFINITE_INTEGRAL,
    "definite integral": ExerciseOperation.DEFINITE_INTEGRAL,
    "integral_definida": ExerciseOperation.DEFINITE_INTEGRAL,
    "unit_conversion": ExerciseOperation.UNIT_CONVERSION,
    "unit conversion": ExerciseOperation.UNIT_CONVERSION,
    "conversao_unidades": ExerciseOperation.UNIT_CONVERSION,
    "simplify": ExerciseOperation.SIMPLIFY,
    "simplification": ExerciseOperation.SIMPLIFY,
    "solve_equation": ExerciseOperation.SOLVE_EQUATION,
    "equation": ExerciseOperation.SOLVE_EQUATION,
}


class StructuredProblemMapper:
    """Safely normalize extracted OCR/LLM fields without evaluating OCR strings."""

    def to_problem(self, exercise: InterpretedExercise, ordinal: int) -> SolutionProblem:
        statement = exercise.statement or "Exercício sem enunciado transcrito."
        problem_type = exercise.problem_type or "unsupported"
        operation = self._operation_for(exercise)
        if operation is ExerciseOperation.UNSUPPORTED:
            return self._unsupported(exercise, ordinal, statement, problem_type)

        try:
            parameters = {
                name: self._to_quantity(quantity)
                for name, quantity in exercise.parameters.items()
            }
        except (InvalidOperation, ValueError):
            return self._unsupported(exercise, ordinal, statement, problem_type)

        expression = _normalize_expression(exercise.expression)
        rhs = _normalize_expression(exercise.rhs)
        lower = _normalize_expression(exercise.lower)
        upper = _normalize_expression(exercise.upper)

        return SolutionProblem(
            ordinal=ordinal,
            statement=statement,
            problem_type=problem_type,
            confidence=exercise.confidence,
            needs_review=exercise.needs_review,
            operation=operation,
            expression=expression,
            variable=exercise.variable.strip() if exercise.variable else None,
            lower=lower,
            upper=upper,
            rhs=rhs,
            parameters=parameters,
            target_unit=exercise.target_unit.strip() if exercise.target_unit else None,
        )

    @staticmethod
    def _operation_for(exercise: InterpretedExercise) -> ExerciseOperation:
        for candidate in (exercise.operation, exercise.problem_type):
            if candidate is None:
                continue
            mapped = _OPERATION_ALIASES.get(candidate.strip().lower())
            if mapped is not None:
                return mapped
        return ExerciseOperation.UNSUPPORTED

    @staticmethod
    def _to_quantity(quantity: ExtractedQuantity) -> PhysicalQuantity:
        normalized = quantity.value.strip().replace(" ", "").replace(",", ".")
        decimal_value = Decimal(normalized)
        return PhysicalQuantity(value=decimal_value, unit=quantity.unit.strip())

    @staticmethod
    def _unsupported(
        exercise: InterpretedExercise,
        ordinal: int,
        statement: str,
        problem_type: str,
    ) -> SolutionProblem:
        return SolutionProblem(
            ordinal=ordinal,
            statement=statement,
            problem_type=problem_type,
            confidence=exercise.confidence,
            needs_review=exercise.needs_review,
            operation=ExerciseOperation.UNSUPPORTED,
        )


def _normalize_expression(raw: str | None) -> str | None:
    if raw is None:
        return None
    normalized = raw.strip().replace("^", "**")
    return normalized or None
