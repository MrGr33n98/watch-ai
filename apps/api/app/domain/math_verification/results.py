"""Immutable result values from independent symbolic verification."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class SymbolicVerification:
    operation: str
    source_expression: str
    result: str
    verified: bool


@dataclass(frozen=True, slots=True)
class DimensionalVerification:
    value: Decimal
    unit: str
    verified: bool
