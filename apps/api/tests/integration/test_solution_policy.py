from decimal import Decimal

import pytest

from app.application.solution_policy import SolutionPolicy
from app.domain.interpretation.models import InterpretationConfidence
from app.domain.math_verification.quantities import PhysicalQuantity
from app.domain.math_verification.solution import (
    ExerciseOperation,
    SolutionProblem,
    SolutionStatus,
    SolutionStepKind,
)


def fourier_problem(**overrides: object) -> SolutionProblem:
    values: dict[str, object] = {
        "ordinal": 1,
        "statement": "Calculate the heat transfer rate through a wall.",
        "problem_type": "Fourier law",
        "confidence": InterpretationConfidence.HIGH,
        "needs_review": False,
        "operation": ExerciseOperation.FOURIER,
        "parameters": {
            "k": PhysicalQuantity(Decimal("1.2"), "W/(m K)"),
            "A": PhysicalQuantity(Decimal("10"), "m^2"),
            "deltaT": PhysicalQuantity(Decimal("40"), "K"),
            "L": PhysicalQuantity(Decimal("0.20"), "m"),
        },
    }
    values.update(overrides)
    return SolutionProblem(**values)  # type: ignore[arg-type]


def test_ambiguous_interpretation_never_produces_a_result() -> None:
    result = SolutionPolicy().solve(
        fourier_problem(confidence=InterpretationConfidence.LOW, needs_review=True)
    )

    assert result.status is SolutionStatus.NEEDS_REVIEW
    assert result.final_answer is None
    assert result.verified is False


def test_missing_fourier_data_requires_review() -> None:
    result = SolutionPolicy().solve(
        fourier_problem(parameters={"k": PhysicalQuantity(Decimal("1.2"), "W/(m K)")})
    )

    assert result.status is SolutionStatus.NEEDS_REVIEW
    assert result.final_answer is None


def test_unsupported_or_hostile_math_requires_review() -> None:
    problem = SolutionProblem(
        ordinal=1,
        statement="Compute the expression.",
        problem_type="derivative",
        confidence=InterpretationConfidence.HIGH,
        needs_review=False,
        operation=ExerciseOperation.DERIVATIVE,
        expression="__import__('os')",
        variable="x",
    )

    result = SolutionPolicy().solve(problem)

    assert result.status is SolutionStatus.NEEDS_REVIEW
    assert result.final_answer is None
    assert result.verified is False


@pytest.mark.parametrize(
    ("problem", "expected_answer", "expected_units"),
    [
        (
            fourier_problem(),
            "2400",
            "W",
        ),
        (
            SolutionProblem(
                ordinal=2,
                statement="Derive f(x) = x^2 + 3x.",
                problem_type="derivative",
                confidence=InterpretationConfidence.HIGH,
                needs_review=False,
                operation=ExerciseOperation.DERIVATIVE,
                expression="x**2 + 3*x",
                variable="x",
            ),
            "2*x + 3",
            None,
        ),
        (
            SolutionProblem(
                ordinal=3,
                statement="Integrate 2x from 0 to 3.",
                problem_type="definite integral",
                confidence=InterpretationConfidence.HIGH,
                needs_review=False,
                operation=ExerciseOperation.DEFINITE_INTEGRAL,
                expression="2*x",
                variable="x",
                lower="0",
                upper="3",
            ),
            "9",
            None,
        ),
        (
            SolutionProblem(
                ordinal=4,
                statement="Convert 1500 W to kW.",
                problem_type="unit conversion",
                confidence=InterpretationConfidence.HIGH,
                needs_review=False,
                operation=ExerciseOperation.UNIT_CONVERSION,
                parameters={"value": PhysicalQuantity(Decimal("1500"), "W")},
                target_unit="kW",
            ),
            "1.5",
            "kW",
        ),
    ],
)
def test_supported_goldens_produce_verified_ordered_steps(
    problem: SolutionProblem,
    expected_answer: str,
    expected_units: str | None,
) -> None:
    result = SolutionPolicy().solve(problem)

    assert result.status is SolutionStatus.READY
    assert result.final_answer == expected_answer
    assert result.units == expected_units
    assert result.verified is True
    assert [step.kind for step in result.steps] == [
        SolutionStepKind.STATEMENT,
        SolutionStepKind.IDENTIFY,
        SolutionStepKind.FORMULA,
        SolutionStepKind.SUBSTITUTION,
        SolutionStepKind.CALCULATION,
        SolutionStepKind.VERIFICATION,
        SolutionStepKind.RESULT,
    ]
