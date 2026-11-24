"""Typed supported-problem inputs and ordered verified-solution values."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from app.domain.interpretation.models import InterpretationConfidence
from app.domain.math_verification.quantities import PhysicalQuantity


class ExerciseOperation(StrEnum):
    FOURIER = "fourier"
    DERIVATIVE = "derivative"
    DEFINITE_INTEGRAL = "definite_integral"
    UNIT_CONVERSION = "unit_conversion"
    UNSUPPORTED = "unsupported"


class SolutionStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"


class SolutionStepKind(StrEnum):
    STATEMENT = "statement"
    IDENTIFY = "identify"
    FORMULA = "formula"
    SUBSTITUTION = "substitution"
    CALCULATION = "calculation"
    VERIFICATION = "verification"
    RESULT = "result"


@dataclass(frozen=True, slots=True)
class SolutionProblem:
    ordinal: int
    statement: str
    problem_type: str
    confidence: InterpretationConfidence
    needs_review: bool
    operation: ExerciseOperation
    expression: str | None = None
    variable: str | None = None
    lower: str | None = None
    upper: str | None = None
    parameters: Mapping[str, PhysicalQuantity] = field(default_factory=dict)
    target_unit: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.ordinal, bool) or not 1 <= self.ordinal <= 4:
            raise ValueError("Question ordinal must be between 1 and 4")
        if not self.statement.strip() or not self.problem_type.strip():
            raise ValueError("Solution problem statement and type must not be empty")
        if self.confidence is InterpretationConfidence.LOW and not self.needs_review:
            raise ValueError("Low-confidence exercise must be marked for review")
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))


@dataclass(frozen=True, slots=True)
class SolutionStep:
    ordinal: int
    kind: SolutionStepKind
    title: str
    plain_text: str
    verified: bool
    latex: str | None = None
    alt_text: str | None = None


@dataclass(frozen=True, slots=True)
class SolvedExercise:
    ordinal: int
    status: SolutionStatus
    verification_status: str
    verified: bool
    final_answer: str | None
    units: str | None
    steps: tuple[SolutionStep, ...]
    review_reason: str | None = None
