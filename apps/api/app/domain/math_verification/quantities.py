"""Exact physical inputs used by the dimensional verifier."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PhysicalQuantity:
    value: Decimal
    unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal) or not self.value.is_finite():
            raise ValueError("Physical quantity value must be a finite Decimal")
        if not self.unit.strip():
            raise ValueError("Physical quantity unit must not be empty")
