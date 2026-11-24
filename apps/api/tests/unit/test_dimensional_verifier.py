from decimal import Decimal

import pytest

from app.adapters.math.dimensional import (
    DimensionalVerifier,
    PhysicalQuantity,
    UnsupportedUnitInput,
)


def test_fourier_law_matches_gold_fourier_001() -> None:
    result = DimensionalVerifier().fourier_heat_rate(
        conductivity=PhysicalQuantity(Decimal("1.2"), "W/(m K)"),
        area=PhysicalQuantity(Decimal("10"), "m^2"),
        delta_temperature=PhysicalQuantity(Decimal("40"), "K"),
        thickness=PhysicalQuantity(Decimal("0.20"), "m"),
    )

    assert result.value == Decimal("2400")
    assert result.unit == "W"
    assert result.verified is True


def test_power_conversion_matches_gold_unit_004() -> None:
    result = DimensionalVerifier().convert(
        PhysicalQuantity(Decimal("1500"), "W"),
        target_unit="kW",
    )

    assert result.value == Decimal("1.5")
    assert result.unit == "kW"


def test_incompatible_dimensions_are_rejected() -> None:
    with pytest.raises(UnsupportedUnitInput):
        DimensionalVerifier().convert(
            PhysicalQuantity(Decimal("1"), "m"),
            target_unit="W",
        )


def test_unknown_unit_text_is_not_parsed_as_an_expression() -> None:
    with pytest.raises(UnsupportedUnitInput):
        DimensionalVerifier().convert(
            PhysicalQuantity(Decimal("1"), "__import__('os')"),
            target_unit="W",
        )
