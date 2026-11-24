"""Exact SymPy operations over the domain's safe typed expression AST."""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

import sympy as sp

from app.domain.math_verification.expressions import (
    DEFAULT_SYMBOLS,
    BinaryExpression,
    ExpressionNode,
    FunctionCall,
    NumberLiteral,
    SafeExpressionParser,
    SafeExpressionRejected,
    SymbolReference,
    UnaryExpression,
)
from app.domain.math_verification.results import SymbolicVerification

_FUNCTIONS: Final[dict[str, Callable[[sp.Expr], sp.Expr]]] = {
    "abs": sp.Abs,
    "cos": sp.cos,
    "exp": sp.exp,
    "log": sp.log,
    "sin": sp.sin,
    "sqrt": sp.sqrt,
    "tan": sp.tan,
}


class UnsupportedMathInput(ValueError):
    """Raised when a safe expression cannot be verified by a supported operation."""


class SymbolicVerifier:
    def __init__(self, parser: SafeExpressionParser | None = None) -> None:
        self._parser = parser or SafeExpressionParser()

    def simplify(self, source_expression: str) -> SymbolicVerification:
        expression = self._parse(source_expression)
        try:
            result = sp.simplify(self._to_sympy(expression))
        except (ArithmeticError, TypeError, ValueError, RecursionError) as error:
            raise UnsupportedMathInput("Expression could not be simplified safely") from error
        return self._result("simplify", source_expression, result)

    def differentiate(self, source_expression: str, *, variable: str) -> SymbolicVerification:
        expression = self._parse(source_expression)
        symbol = self._symbol_for_variable(variable)
        try:
            result = sp.simplify(sp.diff(self._to_sympy(expression), symbol))
        except (ArithmeticError, TypeError, ValueError, RecursionError) as error:
            raise UnsupportedMathInput("Derivative could not be verified") from error
        if result.has(sp.Derivative):
            raise UnsupportedMathInput("Derivative is unsupported by the symbolic verifier")
        return self._result("differentiate", source_expression, result)

    def definite_integral(
        self,
        source_expression: str,
        *,
        variable: str,
        lower: str,
        upper: str,
    ) -> SymbolicVerification:
        expression = self._parse(source_expression)
        symbol = self._symbol_for_variable(variable)
        lower_bound = self._bound(lower)
        upper_bound = self._bound(upper)
        try:
            result = sp.simplify(
                sp.integrate(self._to_sympy(expression), (symbol, lower_bound, upper_bound))
            )
        except (ArithmeticError, TypeError, ValueError, RecursionError) as error:
            raise UnsupportedMathInput("Definite integral could not be verified") from error
        if result.has(sp.Integral):
            raise UnsupportedMathInput("Definite integral is unsupported by the symbolic verifier")
        return self._result("definite_integral", source_expression, result)

    def solve_equation(
        self,
        lhs_expression: str,
        rhs_expression: str,
        *,
        variable: str,
    ) -> SymbolicVerification:
        lhs = self._parse(lhs_expression)
        rhs = self._parse(rhs_expression)
        symbol = self._symbol_for_variable(variable)
        try:
            difference = sp.simplify(self._to_sympy(lhs) - self._to_sympy(rhs))
            if difference == 0 or not difference.has(symbol):
                raise UnsupportedMathInput("Equation has no unique finite solution set")
            solutions = sp.solve(difference, symbol)
        except UnsupportedMathInput:
            raise
        except (ArithmeticError, TypeError, ValueError, RecursionError) as error:
            raise UnsupportedMathInput("Equation could not be solved safely") from error
        if not isinstance(solutions, list) or not (1 <= len(solutions) <= 4):
            raise UnsupportedMathInput("Equation did not yield a bounded solution list")

        verified_roots: list[sp.Expr] = []
        for root in solutions:
            if not isinstance(root, sp.Expr) or root.free_symbols or root.has(sp.I):
                raise UnsupportedMathInput("Equation solution is non-real or symbolic")
            simplified_root = sp.simplify(root)
            if sp.simplify(difference.subs(symbol, simplified_root)) != 0:
                raise UnsupportedMathInput("Equation root failed substitution check")
            verified_roots.append(simplified_root)

        ordered = sorted(verified_roots, key=lambda item: float(sp.N(item)))
        formatted = ", ".join(f"{symbol.name} = {sp.sstr(root)}" for root in ordered)
        return SymbolicVerification(
            operation="solve_equation",
            source_expression=f"{lhs_expression} = {rhs_expression}",
            result=formatted,
            verified=True,
        )

    def _parse(self, source_expression: str) -> ExpressionNode:
        try:
            return self._parser.parse(source_expression)
        except SafeExpressionRejected as error:
            raise UnsupportedMathInput("Expression is outside the safe math grammar") from error

    @staticmethod
    def _symbol_for_variable(variable: str) -> sp.Symbol:
        name = variable.strip()
        if name not in DEFAULT_SYMBOLS or name in {"pi", "E"}:
            raise UnsupportedMathInput("Differentiation variable is unsupported")
        return sp.Symbol(name)

    def _bound(self, source_bound: str) -> sp.Expr:
        expression = self._parse(source_bound)
        value = self._to_sympy(expression)
        if value.free_symbols or value.is_number is not True:
            raise UnsupportedMathInput("Integral bounds must be exact numeric expressions")
        return value

    def _to_sympy(self, expression: ExpressionNode) -> sp.Expr:
        if isinstance(expression, NumberLiteral):
            return sp.Rational(expression.value)
        if isinstance(expression, SymbolReference):
            if expression.name == "pi":
                return sp.pi
            if expression.name == "E":
                return sp.E
            return sp.Symbol(expression.name)
        if isinstance(expression, UnaryExpression):
            operand = self._to_sympy(expression.operand)
            return operand if expression.operator == "+" else -operand
        if isinstance(expression, BinaryExpression):
            left = self._to_sympy(expression.left)
            right = self._to_sympy(expression.right)
            if expression.operator == "+":
                return left + right
            if expression.operator == "-":
                return left - right
            if expression.operator == "*":
                return left * right
            if expression.operator == "/":
                return left / right
            if expression.operator == "**":
                return left**right
            raise UnsupportedMathInput("Binary operation is unsupported")
        if isinstance(expression, FunctionCall):
            function = _FUNCTIONS.get(expression.name)
            if function is None:
                raise UnsupportedMathInput("Math function is unsupported")
            argument = self._to_sympy(expression.arguments[0])
            return function(argument)
        raise UnsupportedMathInput("Expression node is unsupported")

    @staticmethod
    def _result(
        operation: str,
        source_expression: str,
        result: sp.Expr,
    ) -> SymbolicVerification:
        return SymbolicVerification(
            operation=operation,
            source_expression=source_expression,
            result=str(sp.sstr(result)),
            verified=True,
        )
