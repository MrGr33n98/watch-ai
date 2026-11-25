from __future__ import annotations

import pytest

from app.domain.math_verification.expressions import (
    BinaryExpression,
    FunctionCall,
    NumberLiteral,
    SafeExpressionParser,
    SafeExpressionRejected,
    SymbolReference,
    UnaryExpression,
)


def test_parser_builds_only_typed_arithmetic_nodes() -> None:
    expression = SafeExpressionParser().parse("-x + 3 / 4")

    assert isinstance(expression, BinaryExpression)
    assert expression.operator == "+"
    assert isinstance(expression.left, UnaryExpression)
    assert expression.left.operator == "-"
    assert isinstance(expression.left.operand, SymbolReference)
    assert isinstance(expression.right, BinaryExpression)
    assert expression.right.operator == "/"
    assert isinstance(expression.right.left, NumberLiteral)


@pytest.mark.parametrize(
    "source",
    [
        "__import__('os')",
        "x.__class__",
        "eval('1 + 1')",
        "open('/etc/passwd')",
        "sin(x, y)",
        "x[0]",
    ],
)
def test_parser_rejects_calls_attributes_and_other_python_syntax(source: str) -> None:
    with pytest.raises(SafeExpressionRejected):
        SafeExpressionParser().parse(source)


def test_parser_rejects_unknown_symbols_and_boolean_literals() -> None:
    parser = SafeExpressionParser()

    with pytest.raises(SafeExpressionRejected):
        parser.parse("x + secret")
    with pytest.raises(SafeExpressionRejected):
        parser.parse("True + 1")


def test_parser_accepts_only_whitelisted_math_functions() -> None:
    expression = SafeExpressionParser().parse("sqrt(x**2) + sin(pi)")

    assert isinstance(expression, BinaryExpression)
    assert isinstance(expression.left, FunctionCall)
    assert expression.left.name == "sqrt"


def test_parser_rejects_excessive_depth_size_and_power() -> None:
    parser = SafeExpressionParser(max_depth=8, max_nodes=128, max_source_chars=256)

    with pytest.raises(SafeExpressionRejected):
        parser.parse("sqrt(" * 9 + "x" + ")" * 9)
    with pytest.raises(SafeExpressionRejected):
        parser.parse("x + 1001**1001")

    with pytest.raises(SafeExpressionRejected):
        SafeExpressionParser(max_source_chars=8).parse("x + 123456789")
