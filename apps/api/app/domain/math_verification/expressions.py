"""A bounded arithmetic AST parser that never evaluates OCR-provided Python."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

DEFAULT_SYMBOLS = frozenset(
    {
        "A",
        "E",
        "L",
        "a",
        "b",
        "c",
        "dT",
        "k",
        "m",
        "n",
        "pi",
        "r",
        "s",
        "t",
        "theta",
        "v",
        "x",
        "y",
        "z",
    }
)
SAFE_FUNCTIONS = frozenset({"abs", "cos", "exp", "log", "sin", "sqrt", "tan"})
_BINARY_OPERATORS = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.Pow: "**",
}
_UNARY_OPERATORS = {ast.UAdd: "+", ast.USub: "-"}
MAX_NUMERIC_DIGITS = 64
MAX_NUMERIC_MAGNITUDE = 1000
MAX_POWER_EXPONENT = Decimal(1000)


class SafeExpressionRejected(ValueError):
    """Raised when expression text exceeds the safe arithmetic grammar."""


@dataclass(frozen=True, slots=True)
class NumberLiteral:
    value: str


@dataclass(frozen=True, slots=True)
class SymbolReference:
    name: str


@dataclass(frozen=True, slots=True)
class UnaryExpression:
    operator: str
    operand: ExpressionNode


@dataclass(frozen=True, slots=True)
class BinaryExpression:
    operator: str
    left: ExpressionNode
    right: ExpressionNode


@dataclass(frozen=True, slots=True)
class FunctionCall:
    name: str
    arguments: tuple[ExpressionNode, ...]


type ExpressionNode = (
    NumberLiteral | SymbolReference | UnaryExpression | BinaryExpression | FunctionCall
)


class SafeExpressionParser:
    def __init__(
        self,
        *,
        symbols: frozenset[str] = DEFAULT_SYMBOLS,
        max_depth: int = 32,
        max_nodes: int = 128,
        max_source_chars: int = 512,
    ) -> None:
        if max_depth < 1 or max_nodes < 1 or max_source_chars < 1:
            raise ValueError("Expression parser limits must be positive")
        self._symbols = symbols
        self._max_depth = max_depth
        self._max_nodes = max_nodes
        self._max_source_chars = max_source_chars

    def parse(self, source: str) -> ExpressionNode:
        normalized = source.strip()
        if not normalized:
            raise SafeExpressionRejected("Expression must not be empty")
        if len(normalized) > self._max_source_chars:
            raise SafeExpressionRejected("Expression exceeds the source length limit")
        try:
            syntax_tree = ast.parse(normalized, mode="eval")
        except (SyntaxError, ValueError, RecursionError) as error:
            raise SafeExpressionRejected("Expression syntax is invalid") from error
        if sum(1 for _ in ast.walk(syntax_tree)) > self._max_nodes:
            raise SafeExpressionRejected("Expression exceeds the AST node limit")
        return self._build(syntax_tree.body, normalized, depth=1)

    def _build(self, node: ast.AST, source: str, depth: int) -> ExpressionNode:
        if depth > self._max_depth:
            raise SafeExpressionRejected("Expression exceeds the AST depth limit")
        if isinstance(node, ast.Constant):
            return self._number_literal(node, source)
        if isinstance(node, ast.Name):
            if node.id not in self._symbols:
                raise SafeExpressionRejected("Expression contains an unknown symbol")
            return SymbolReference(node.id)
        if isinstance(node, ast.UnaryOp):
            operator = _UNARY_OPERATORS.get(type(node.op))
            if operator is None:
                raise SafeExpressionRejected("Unary operator is not allowed")
            return UnaryExpression(
                operator=operator,
                operand=self._build(node.operand, source, depth + 1),
            )
        if isinstance(node, ast.BinOp):
            operator = _BINARY_OPERATORS.get(type(node.op))
            if operator is None:
                raise SafeExpressionRejected("Binary operator is not allowed")
            if operator == "**":
                self._validate_power_exponent(node.right, source)
            return BinaryExpression(
                operator=operator,
                left=self._build(node.left, source, depth + 1),
                right=self._build(node.right, source, depth + 1),
            )
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_FUNCTIONS:
                raise SafeExpressionRejected("Function call is not allowed")
            if node.keywords or len(node.args) != 1:
                raise SafeExpressionRejected("Math functions require one positional argument")
            return FunctionCall(
                name=node.func.id,
                arguments=(self._build(node.args[0], source, depth + 1),),
            )
        raise SafeExpressionRejected("Expression contains unsupported syntax")

    @staticmethod
    def _number_literal(node: ast.Constant, source: str) -> NumberLiteral:
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise SafeExpressionRejected("Only numeric literals are allowed")
        literal = ast.get_source_segment(source, node)
        if literal is None:
            raise SafeExpressionRejected("Numeric literal could not be read")
        try:
            value = Decimal(literal)
        except InvalidOperation as error:
            raise SafeExpressionRejected("Numeric literal is invalid") from error
        digits = sum(character.isdigit() for character in literal)
        if not value.is_finite() or digits > MAX_NUMERIC_DIGITS:
            raise SafeExpressionRejected("Numeric literal exceeds the safe range")
        if value != 0 and abs(value.adjusted()) > MAX_NUMERIC_MAGNITUDE:
            raise SafeExpressionRejected("Numeric literal magnitude exceeds the safe range")
        return NumberLiteral(literal)

    @classmethod
    def _validate_power_exponent(cls, node: ast.expr, source: str) -> None:
        sign = Decimal(1)
        literal_node: ast.expr = node
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            sign = Decimal(-1)
            literal_node = node.operand
        if not isinstance(literal_node, ast.Constant):
            return
        if isinstance(literal_node.value, bool) or not isinstance(
            literal_node.value,
            (int, float),
        ):
            return
        literal = ast.get_source_segment(source, literal_node)
        if literal is None:
            raise SafeExpressionRejected("Power exponent could not be read")
        try:
            exponent = sign * Decimal(literal)
        except InvalidOperation as error:
            raise SafeExpressionRejected("Power exponent is invalid") from error
        if not exponent.is_finite() or abs(exponent) > MAX_POWER_EXPONENT:
            raise SafeExpressionRejected("Power exponent exceeds the safe range")
