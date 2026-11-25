from __future__ import annotations

from decimal import Decimal

from app.application.problem_mapper import StructuredProblemMapper
from app.domain.interpretation.models import (
    ExtractedQuantity,
    InterpretationConfidence,
    InterpretedExercise,
)
from app.domain.math_verification.solution import ExerciseOperation


def test_mapper_builds_fourier_problem_with_comma_decimals() -> None:
    exercise = InterpretedExercise(
        statement="Parede: k=1,2 W/(m K), A=10 m^2, deltaT=40 K, L=0,20 m.",
        problem_type="Fourier law",
        confidence=InterpretationConfidence.HIGH,
        needs_review=False,
        operation="fourier",
        parameters={
            "k": ExtractedQuantity("1,2", "W/(m K)"),
            "A": ExtractedQuantity("10", "m^2"),
            "deltaT": ExtractedQuantity("40", "K"),
            "L": ExtractedQuantity("0,20", "m"),
        },
    )

    problem = StructuredProblemMapper().to_problem(exercise, ordinal=1)

    assert problem.operation is ExerciseOperation.FOURIER
    assert problem.parameters["k"].value == Decimal("1.2")
    assert problem.parameters["L"].value == Decimal("0.20")


def test_mapper_builds_equation_and_normalizes_caret_exponent() -> None:
    exercise = InterpretedExercise(
        statement="Resolva x^2 - 9 = 0.",
        problem_type="equation",
        confidence=InterpretationConfidence.HIGH,
        needs_review=False,
        operation="solve_equation",
        expression="x^2 - 9",
        rhs="0",
        variable="x",
    )

    problem = StructuredProblemMapper().to_problem(exercise, ordinal=2)

    assert problem.operation is ExerciseOperation.SOLVE_EQUATION
    assert problem.expression == "x**2 - 9"
    assert problem.rhs == "0"
    assert problem.variable == "x"


def test_mapper_falls_back_to_unsupported_on_invalid_number_or_missing_op() -> None:
    exercise = InterpretedExercise(
        statement="Parede com k inválido.",
        problem_type="Fourier law",
        confidence=InterpretationConfidence.HIGH,
        needs_review=False,
        operation="fourier",
        parameters={"k": ExtractedQuantity("abc", "W/(m K)")},
    )

    problem = StructuredProblemMapper().to_problem(exercise, ordinal=1)

    assert problem.operation is ExerciseOperation.UNSUPPORTED
