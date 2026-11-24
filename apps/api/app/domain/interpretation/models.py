"""Typed, uncertainty-aware result of reading a photographed exercise."""

from dataclasses import dataclass
from enum import StrEnum


class InterpretationConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class InterpretedExercise:
    statement: str | None
    problem_type: str | None
    confidence: InterpretationConfidence
    needs_review: bool

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
