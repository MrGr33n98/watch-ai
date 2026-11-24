"""Typed, uncertainty-aware result of reading a photographed exercise."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType


class InterpretationConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class ExtractedQuantity:
    value: str
    unit: str


@dataclass(frozen=True, slots=True)
class InterpretedExercise:
    statement: str | None
    problem_type: str | None
    confidence: InterpretationConfidence
    needs_review: bool
    operation: str | None = None
    expression: str | None = None
    variable: str | None = None
    lower: str | None = None
    upper: str | None = None
    rhs: str | None = None
    target_unit: str | None = None
    parameters: Mapping[str, ExtractedQuantity] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.statement is not None and not self.statement.strip():
            raise ValueError("Interpreted statement must be null or non-empty")
        if self.problem_type is not None and not self.problem_type.strip():
            raise ValueError("Problem type must be null or non-empty")
        if self.confidence is InterpretationConfidence.HIGH and (
            self.statement is None or self.problem_type is None
        ):
            raise ValueError("High-confidence interpretation requires a statement and type")
        if self.confidence is InterpretationConfidence.LOW and not self.needs_review:
            raise ValueError("Low-confidence interpretation must be marked for review")
        if (self.statement is None or self.problem_type is None) and not self.needs_review:
            raise ValueError("Incomplete interpretation must be marked for review")
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))
