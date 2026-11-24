"""Pint dimensional checks over explicit unit aliases and Decimal magnitudes."""

from decimal import Decimal, InvalidOperation, localcontext

import pint
from pint import UnitRegistry

from app.domain.math_verification.quantities import PhysicalQuantity
from app.domain.math_verification.results import DimensionalVerification


class UnsupportedUnitInput(ValueError):
    """Raised for unknown units or incompatible dimensions."""


class DimensionalVerifier:
    def __init__(self, decimal_precision: int = 28) -> None:
        if isinstance(decimal_precision, bool) or decimal_precision < 1:
            raise ValueError("Decimal precision must be a positive integer")
        self._decimal_precision = decimal_precision
        self._units = UnitRegistry(non_int_type=Decimal)
        self._unit_aliases = {
            "K": self._units.kelvin,
            "W": self._units.watt,
            "W/(m K)": self._units.watt / self._units.meter / self._units.kelvin,
            "kW": self._units.kilowatt,
            "kelvin": self._units.kelvin,
            "m": self._units.meter,
            "m^2": self._units.meter**2,
            "meter": self._units.meter,
            "square_meter": self._units.meter**2,
            "watt": self._units.watt,
            "watt_per_meter_kelvin": (
                self._units.watt / self._units.meter / self._units.kelvin
            ),
        }

    def convert(
        self,
        quantity: PhysicalQuantity,
        *,
        target_unit: str,
    ) -> DimensionalVerification:
        source = self._quantity(quantity)
        target = self._unit(target_unit)
        try:
            with localcontext() as context:
                context.prec = self._decimal_precision
                converted = source.to(target)
        except (pint.DimensionalityError, ArithmeticError, InvalidOperation) as error:
            raise UnsupportedUnitInput("Source and target units are incompatible") from error
        return self._result(converted, target_unit)

    def fourier_heat_rate(
        self,
        *,
        conductivity: PhysicalQuantity,
        area: PhysicalQuantity,
        delta_temperature: PhysicalQuantity,
        thickness: PhysicalQuantity,
    ) -> DimensionalVerification:
        try:
            with localcontext() as context:
                context.prec = self._decimal_precision
                heat_rate = (
                    self._quantity(conductivity)
                    * self._quantity(area)
                    * self._quantity(delta_temperature)
                    / self._quantity(thickness)
                ).to(self._units.watt)
        except (pint.DimensionalityError, ArithmeticError, InvalidOperation) as error:
            raise UnsupportedUnitInput(
                "Fourier law inputs have incompatible dimensions or zero thickness"
            ) from error
        return self._result(heat_rate, "W")

    def _quantity(self, quantity: PhysicalQuantity) -> pint.Quantity:
        return self._units.Quantity(quantity.value, self._unit(quantity.unit))

    def _unit(self, unit_name: str) -> pint.Unit:
        unit = self._unit_aliases.get(unit_name.strip())
        if unit is None:
            raise UnsupportedUnitInput("Unit is not in the supported unit allowlist")
        return unit

    @staticmethod
    def _result(quantity: pint.Quantity, unit_name: str) -> DimensionalVerification:
        value = quantity.magnitude
        if not isinstance(value, Decimal) or not value.is_finite():
            raise UnsupportedUnitInput("Pint returned a non-finite or non-Decimal result")
        return DimensionalVerification(value=value.normalize(), unit=unit_name, verified=True)
