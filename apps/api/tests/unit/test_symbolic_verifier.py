import pytest

from app.adapters.math.symbolic import SymbolicVerifier, UnsupportedMathInput


def test_derivative_matches_gold_derivative_002() -> None:
    result = SymbolicVerifier().differentiate("x**2 + 3*x", variable="x")

    assert result.verified is True
    assert result.result == "2*x + 3"


def test_definite_integral_matches_gold_integral_003() -> None:
    result = SymbolicVerifier().definite_integral(
        "2*x",
        variable="x",
        lower="0",
        upper="3",
    )

    assert result.verified is True
    assert result.result == "9"


def test_supported_algebra_is_simplified_exactly() -> None:
    result = SymbolicVerifier().simplify("x**2 - x*x + 4")

    assert result.verified is True
    assert result.result == "4"


def test_unsupported_syntax_is_not_sent_to_sympy_as_code() -> None:
    with pytest.raises(UnsupportedMathInput):
        SymbolicVerifier().differentiate("x // 2", variable="x")


def test_definite_integral_requires_numeric_bounds() -> None:
    with pytest.raises(UnsupportedMathInput):
        SymbolicVerifier().definite_integral(
            "x",
            variable="x",
            lower="x",
            upper="3",
        )
