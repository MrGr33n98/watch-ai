"""Safe small-subset math rendering with private SVG storage and text fallback."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import mkstemp
from xml.sax.saxutils import escape

MAX_FORMULA_CHARS = 512
MAX_FALLBACK_CHARS = 1000
MAX_ALT_TEXT_CHARS = 500
MAX_SVG_WIDTH = 2048
DEFAULT_MAX_ASSET_BYTES = 32 * 1024
_GREEK = {
    "Alpha": "Α",
    "Beta": "Β",
    "Delta": "Δ",
    "Gamma": "Γ",
    "Lambda": "Λ",
    "Omega": "Ω",
    "Phi": "Φ",
    "Pi": "Π",
    "Sigma": "Σ",
    "Theta": "Θ",
    "alpha": "α",
    "beta": "β",
    "delta": "δ",
    "epsilon": "ε",
    "eta": "η",
    "gamma": "γ",
    "kappa": "κ",
    "lambda": "λ",
    "mu": "μ",
    "nu": "ν",
    "omega": "ω",
    "phi": "φ",
    "pi": "π",
    "rho": "ρ",
    "sigma": "σ",
    "tau": "τ",
    "theta": "θ",
    "zeta": "ζ",
}
_SIMPLE_COMMANDS = {
    "approx": "≈",
    "cap": "∩",
    "cdot": "·",
    "cup": "∪",
    "equiv": "≡",
    "ge": "≥",
    "geq": "≥",
    "in": "∈",
    "infty": "∞",
    "int": "∫",
    "le": "≤",
    "leq": "≤",
    "lim": "lim",
    "nabla": "∇",
    "neq": "≠",
    "partial": "∂",
    "pm": "±",
    "prod": "∏",
    "quad": "   ",
    "qquad": "      ",
    "rightarrow": "→",
    "sum": "∑",
    "times": "×",
    "to": "→",
}
_SUBSCRIPTS = {
    "0": "₀",
    "1": "₁",
    "2": "₂",
    "3": "₃",
    "4": "₄",
    "5": "₅",
    "6": "₆",
    "7": "₇",
    "8": "₈",
    "9": "₉",
    "+": "₊",
    "-": "₋",
    "=": "₌",
    "(": "₍",
    ")": "₎",
    "a": "ₐ",
    "e": "ₑ",
    "h": "ₕ",
    "i": "ᵢ",
    "j": "ⱼ",
    "k": "ₖ",
    "l": "ₗ",
    "m": "ₘ",
    "n": "ₙ",
    "o": "ₒ",
    "p": "ₚ",
    "r": "ᵣ",
    "s": "ₛ",
    "t": "ₜ",
    "u": "ᵤ",
    "v": "ᵥ",
    "x": "ₓ",
}
_SUPERSCRIPTS = {
    "0": "⁰",
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹",
    "+": "⁺",
    "-": "⁻",
    "=": "⁼",
    "(": "⁽",
    ")": "⁾",
    "i": "ⁱ",
    "n": "ⁿ",
}


class UnsupportedFormula(ValueError):
    """Raised internally when LaTeX falls outside the safe rendering subset."""


class FormulaAssetTooLarge(ValueError):
    """Raised when an SVG asset exceeds the configured private-storage limit."""


@dataclass(frozen=True, slots=True)
class FormulaRenderResult:
    latex: str | None
    plain_text: str
    alt_text: str
    asset_key: str | None
    rendered: bool


class PrivateFormulaAssetStore:
    def __init__(self, root: Path, max_bytes: int = DEFAULT_MAX_ASSET_BYTES) -> None:
        if isinstance(max_bytes, bool) or max_bytes < 1:
            raise ValueError("Formula asset byte limit must be positive")
        self._root = root.expanduser().resolve()
        self._root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self._root, 0o700)
        self._max_bytes = max_bytes

    def store(self, content: bytes) -> str:
        if not content or len(content) > self._max_bytes:
            raise FormulaAssetTooLarge("Formula SVG is empty or exceeds the asset byte limit")
        asset_key = f"{sha256(content).hexdigest()}.svg"
        destination = self.path_for(asset_key)
        descriptor, temporary_name = mkstemp(prefix=".formula-", dir=self._root)
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as asset_file:
                asset_file.write(content)
                asset_file.flush()
                os.fsync(asset_file.fileno())
            os.replace(temporary_path, destination)
        finally:
            temporary_path.unlink(missing_ok=True)
        return asset_key

    def path_for(self, asset_key: str) -> Path:
        if re.fullmatch(r"[a-f0-9]{64}\.svg", asset_key) is None:
            raise ValueError("Formula asset key is invalid")
        path = (self._root / asset_key).resolve()
        if path.parent != self._root:
            raise ValueError("Formula asset path escapes the private storage root")
        return path


class FormulaRenderer:
    def __init__(
        self,
        asset_store: PrivateFormulaAssetStore,
        *,
        max_formula_chars: int = MAX_FORMULA_CHARS,
    ) -> None:
        if isinstance(max_formula_chars, bool) or max_formula_chars < 1:
            raise ValueError("Formula source length limit must be positive")
        self._asset_store = asset_store
        self._max_formula_chars = max_formula_chars

    def render(
        self,
        *,
        latex: str | None,
        fallback_text: str,
        alt_text: str,
    ) -> FormulaRenderResult:
        fallback = self._bounded_text(fallback_text, MAX_FALLBACK_CHARS)
        accessible_text = self._bounded_text(alt_text, MAX_ALT_TEXT_CHARS)
        if latex is None or len(latex) > self._max_formula_chars:
            return FormulaRenderResult(None, fallback, accessible_text, None, False)
        try:
            plain_text = _LatexTextParser(latex).parse()
            svg = self._svg(plain_text, accessible_text)
            asset_key = self._asset_store.store(svg)
        except (UnsupportedFormula, FormulaAssetTooLarge, ValueError):
            return FormulaRenderResult(latex, fallback, accessible_text, None, False)
        return FormulaRenderResult(latex, plain_text, accessible_text, asset_key, True)

    @staticmethod
    def _bounded_text(value: str, limit: int) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            return "Formula text unavailable"
        return normalized[:limit]

    @staticmethod
    def _svg(plain_text: str, alt_text: str) -> bytes:
        estimated_width = max(128, len(plain_text) * 20 + 32)
        if estimated_width > MAX_SVG_WIDTH:
            raise UnsupportedFormula("Formula is too wide for the bounded SVG canvas")
        width = estimated_width
        escaped_text = escape(plain_text)
        escaped_alt = escape(alt_text, {"\"": "&quot;", "'": "&apos;"})
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="64" '
            f'viewBox="0 0 {width} 64" role="img" aria-label="{escaped_alt}">'
            f"<title>{escaped_alt}</title>"
            f'<text x="12" y="44" font-family="sans-serif" font-size="32">'
            f"{escaped_text}</text></svg>"
        ).encode()


class _LatexTextParser:
    def __init__(self, source: str) -> None:
        self._source = source
        self._position = 0

    def parse(self) -> str:
        if not self._source.strip():
            raise UnsupportedFormula("Formula is empty")
        result = self._sequence(stop_at_brace=False)
        if self._position != len(self._source):
            raise UnsupportedFormula("Formula could not be fully parsed")
        normalized = " ".join(result.split())
        if not normalized:
            raise UnsupportedFormula("Formula has no printable content")
        return normalized

    def _sequence(self, *, stop_at_brace: bool) -> str:
        result: list[str] = []
        while self._position < len(self._source):
            character = self._source[self._position]
            if character == "}":
                if not stop_at_brace:
                    raise UnsupportedFormula("Unexpected closing brace")
                self._position += 1
                return "".join(result)
            if character == "{":
                self._position += 1
                result.append(self._sequence(stop_at_brace=True))
            elif character == "\\":
                result.append(self._command())
            elif character in "_^":
                marker = character
                self._position += 1
                script = self._script_argument()
                result.append(self._script(marker, script))
            elif character.isalnum() or character.isspace() or character in "+-=*/(),.[]|':;":
                result.append(character)
                self._position += 1
            else:
                raise UnsupportedFormula("Formula contains unsupported characters")
        if stop_at_brace:
            raise UnsupportedFormula("Formula contains an unmatched opening brace")
        return "".join(result)

    def _command(self) -> str:
        self._position += 1
        if self._position >= len(self._source):
            raise UnsupportedFormula("Formula ends with an incomplete command")
        start = self._position
        if self._source[self._position].isalpha():
            while self._position < len(self._source) and self._source[self._position].isalpha():
                self._position += 1
            name = self._source[start : self._position]
        else:
            name = self._source[self._position]
            self._position += 1
        if name.isalpha():
            while self._position < len(self._source) and self._source[self._position].isspace():
                self._position += 1

        if name in _GREEK:
            return _GREEK[name]
        if name in _SIMPLE_COMMANDS:
            return _SIMPLE_COMMANDS[name]
        if name in {",", ";", "!", " "}:
            return " " if name in {",", ";", " "} else ""
        if name in {"left", "right", "limits", "displaystyle", "textstyle"}:
            return ""
        if name in {
            "frac",
            "sqrt",
            "mathrm",
            "text",
            "dot",
            "ddot",
            "vec",
            "boxed",
            "overline",
        }:
            argument = self._required_group()
            if name == "frac":
                denominator = self._required_group()
                return f"({argument})/({denominator})"
            if name == "sqrt":
                return f"√({argument})"
            if name == "dot":
                return f"{argument}\u0307"
            if name == "ddot":
                return f"{argument}\u0308"
            if name == "vec":
                return f"{argument}\u20D7"
            if name == "boxed":
                return f"[{argument}]"
            if name == "overline":
                return f"¯({argument})"
            return argument
        raise UnsupportedFormula("Formula uses an unsupported LaTeX command")

    def _required_group(self) -> str:
        if self._position >= len(self._source) or self._source[self._position] != "{":
            raise UnsupportedFormula("LaTeX command requires a braced argument")
        self._position += 1
        return self._sequence(stop_at_brace=True)

    def _script_argument(self) -> str:
        if self._position >= len(self._source):
            raise UnsupportedFormula("Formula ends with an incomplete script")
        if self._source[self._position] == "{":
            return self._required_group()
        character = self._source[self._position]
        if not character.isalnum():
            raise UnsupportedFormula("Unbraced script is unsupported")
        self._position += 1
        return character

    @staticmethod
    def _script(marker: str, value: str) -> str:
        translations = _SUBSCRIPTS if marker == "_" else _SUPERSCRIPTS
        try:
            return "".join(translations[character] for character in value)
        except KeyError:
            opening, closing = ("_(", ")") if marker == "_" else ("^(", ")")
            return f"{opening}{value}{closing}"
