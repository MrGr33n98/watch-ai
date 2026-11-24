"""Safe application policy for exact, ordered exercise solutions."""

from decimal import Decimal

from app.adapters.math.dimensional import DimensionalVerifier, UnsupportedUnitInput
from app.adapters.math.symbolic import SymbolicVerifier, UnsupportedMathInput
from app.domain.math_verification.quantities import PhysicalQuantity
from app.domain.math_verification.solution import (
    ExerciseOperation,
    SolutionProblem,
    SolutionStatus,
    SolutionStep,
    SolutionStepKind,
    SolvedExercise,
)


class SolutionPolicy:
    def __init__(
        self,
        symbolic_verifier: SymbolicVerifier | None = None,
        dimensional_verifier: DimensionalVerifier | None = None,
    ) -> None:
        self._symbolic = symbolic_verifier or SymbolicVerifier()
        self._dimensional = dimensional_verifier or DimensionalVerifier()

    def solve(self, problem: SolutionProblem) -> SolvedExercise:
        if problem.needs_review or problem.confidence.value != "high":
            return self._review(problem, "interpretation_ambiguous")
        if problem.operation is ExerciseOperation.UNSUPPORTED:
            return self._review(problem, "unsupported_operation")

        try:
            match problem.operation:
                case ExerciseOperation.FOURIER:
                    return self._solve_fourier(problem)
                case ExerciseOperation.DERIVATIVE:
                    return self._solve_derivative(problem)
                case ExerciseOperation.DEFINITE_INTEGRAL:
                    return self._solve_integral(problem)
                case ExerciseOperation.UNIT_CONVERSION:
                    return self._solve_conversion(problem)
                case _:
                    return self._review(problem, "unsupported_operation")
        except (UnsupportedMathInput, UnsupportedUnitInput, ArithmeticError, ValueError):
            return self._review(problem, "unsupported_or_inconsistent_input")

    def _solve_fourier(self, problem: SolutionProblem) -> SolvedExercise:
        required = {"k", "A", "deltaT", "L"}
        if set(problem.parameters) != required:
            return self._review(problem, "missing_data")
        conductivity = problem.parameters["k"]
        area = problem.parameters["A"]
        delta_temperature = problem.parameters["deltaT"]
        thickness = problem.parameters["L"]
        result = self._dimensional.fourier_heat_rate(
            conductivity=conductivity,
            area=area,
            delta_temperature=delta_temperature,
            thickness=thickness,
        )
        data = "; ".join(
            (
                f"k = {self._quantity_text(conductivity)}",
                f"A = {self._quantity_text(area)}",
                f"ΔT = {self._quantity_text(delta_temperature)}",
                f"L = {self._quantity_text(thickness)}",
            )
        )
        substituted = (
            f"Q̇ = {self._number_text(conductivity.value)} × "
            f"{self._number_text(area.value)} × {self._number_text(delta_temperature.value)} / "
            f"{self._number_text(thickness.value)}"
        )
        answer = self._number_text(result.value)
        return self._ready(
            problem,
            answer,
            result.unit,
            (
                (SolutionStepKind.STATEMENT, "Enunciado", problem.statement, None, False),
                (SolutionStepKind.IDENTIFY, "Identificar dados", data, None, False),
                (
                    SolutionStepKind.FORMULA,
                    "Fórmula",
                    "Q̇ = k × A × ΔT / L",
                    r"\dot{Q}=kA\frac{\Delta T}{L}",
                    False,
                ),
                (
                    SolutionStepKind.SUBSTITUTION,
                    "Substituição",
                    substituted,
                    None,
                    False,
                ),
                (
                    SolutionStepKind.CALCULATION,
                    "Cálculo",
                    f"Q̇ = {answer} {result.unit}",
                    None,
                    True,
                ),
                (
                    SolutionStepKind.VERIFICATION,
                    "Verificação dimensional",
                    "Pint confirmou que as dimensões resultam em watts.",
                    None,
                    True,
                ),
                (
                    SolutionStepKind.RESULT,
                    "Resultado",
                    f"Q̇ = {answer} {result.unit}",
                    None,
                    True,
                ),
            ),
        )

    def _solve_derivative(self, problem: SolutionProblem) -> SolvedExercise:
        if problem.expression is None or problem.variable is None:
            return self._review(problem, "missing_data")
        result = self._symbolic.differentiate(problem.expression, variable=problem.variable)
        answer = result.result
        return self._ready(
            problem,
            answer,
            None,
            (
                (SolutionStepKind.STATEMENT, "Enunciado", problem.statement, None, False),
                (
                    SolutionStepKind.IDENTIFY,
                    "Identificar dados",
                    f"Variável: {problem.variable}",
                    None,
                    False,
                ),
                (
                    SolutionStepKind.FORMULA,
                    "Operação",
                    f"Derivar em relação a {problem.variable}: {problem.expression}",
                    None,
                    False,
                ),
                (
                    SolutionStepKind.SUBSTITUTION,
                    "Expressão",
                    f"d/d{problem.variable} ({problem.expression})",
                    None,
                    False,
                ),
                (
                    SolutionStepKind.CALCULATION,
                    "Cálculo",
                    answer,
                    None,
                    True,
                ),
                (
                    SolutionStepKind.VERIFICATION,
                    "Verificação simbólica",
                    "SymPy calculou a derivada exata sem termos não resolvidos.",
                    None,
                    True,
                ),
                (SolutionStepKind.RESULT, "Resultado", answer, None, True),
            ),
        )

    def _solve_integral(self, problem: SolutionProblem) -> SolvedExercise:
        if (
            problem.expression is None
            or problem.variable is None
            or problem.lower is None
            or problem.upper is None
        ):
            return self._review(problem, "missing_data")
        result = self._symbolic.definite_integral(
            problem.expression,
            variable=problem.variable,
            lower=problem.lower,
            upper=problem.upper,
        )
        answer = result.result
        integral = f"∫[{problem.lower}, {problem.upper}] {problem.expression} d{problem.variable}"
        return self._ready(
            problem,
            answer,
            None,
            (
                (SolutionStepKind.STATEMENT, "Enunciado", problem.statement, None, False),
                (
                    SolutionStepKind.IDENTIFY,
                    "Identificar dados",
                    f"Intervalo: [{problem.lower}, {problem.upper}]; variável: {problem.variable}",
                    None,
                    False,
                ),
                (SolutionStepKind.FORMULA, "Integral definida", integral, None, False),
                (SolutionStepKind.SUBSTITUTION, "Integrando", problem.expression, None, False),
                (SolutionStepKind.CALCULATION, "Cálculo", answer, None, True),
                (
                    SolutionStepKind.VERIFICATION,
                    "Verificação simbólica",
                    "SymPy avaliou a integral definida exatamente.",
                    None,
                    True,
                ),
                (SolutionStepKind.RESULT, "Resultado", answer, None, True),
            ),
        )

    def _solve_conversion(self, problem: SolutionProblem) -> SolvedExercise:
        quantity = problem.parameters.get("value")
        if quantity is None or problem.target_unit is None:
            return self._review(problem, "missing_data")
        if set(problem.parameters) != {"value"}:
            return self._review(problem, "unsupported_data")
        result = self._dimensional.convert(quantity, target_unit=problem.target_unit)
        answer = self._number_text(result.value)
        input_text = self._quantity_text(quantity)
        return self._ready(
            problem,
            answer,
            result.unit,
            (
                (SolutionStepKind.STATEMENT, "Enunciado", problem.statement, None, False),
                (SolutionStepKind.IDENTIFY, "Identificar dados", input_text, None, False),
                (
                    SolutionStepKind.FORMULA,
                    "Conversão de unidades",
                    f"Converter {quantity.unit} para {result.unit}",
                    None,
                    False,
                ),
                (
                    SolutionStepKind.SUBSTITUTION,
                    "Substituição",
                    f"{input_text} → {result.unit}",
                    None,
                    False,
                ),
                (
                    SolutionStepKind.CALCULATION,
                    "Cálculo",
                    f"{answer} {result.unit}",
                    None,
                    True,
                ),
                (
                    SolutionStepKind.VERIFICATION,
                    "Verificação dimensional",
                    "Pint confirmou que as unidades têm dimensões compatíveis.",
                    None,
                    True,
                ),
                (
                    SolutionStepKind.RESULT,
                    "Resultado",
                    f"{answer} {result.unit}",
                    None,
                    True,
                ),
            ),
        )

    def _ready(
        self,
        problem: SolutionProblem,
        final_answer: str,
        units: str | None,
        step_data: tuple[tuple[SolutionStepKind, str, str, str | None, bool], ...],
    ) -> SolvedExercise:
        steps = tuple(
            SolutionStep(
                ordinal=index,
                kind=kind,
                title=title,
                plain_text=plain_text,
                latex=latex,
                alt_text=plain_text,
                verified=verified,
            )
            for index, (kind, title, plain_text, latex, verified) in enumerate(step_data, start=1)
        )
        return SolvedExercise(
            ordinal=problem.ordinal,
            status=SolutionStatus.READY,
            verification_status="verified",
            verified=True,
            final_answer=final_answer,
            units=units,
            steps=steps,
        )

    @staticmethod
    def _review(problem: SolutionProblem, reason: str) -> SolvedExercise:
        return SolvedExercise(
            ordinal=problem.ordinal,
            status=SolutionStatus.NEEDS_REVIEW,
            verification_status="inconclusive",
            verified=False,
            final_answer=None,
            units=None,
            steps=(
                SolutionStep(
                    ordinal=1,
                    kind=SolutionStepKind.STATEMENT,
                    title="Enunciado",
                    plain_text=problem.statement,
                    alt_text=problem.statement,
                    verified=False,
                ),
                SolutionStep(
                    ordinal=2,
                    kind=SolutionStepKind.VERIFICATION,
                    title="Revisão necessária",
                    plain_text="Não há resultado verificado para esta questão.",
                    alt_text="A questão precisa ser revisada antes de exibir um resultado.",
                    verified=False,
                ),
            ),
            review_reason=reason,
        )

    @classmethod
    def _quantity_text(cls, quantity: PhysicalQuantity) -> str:
        return f"{cls._number_text(quantity.value)} {quantity.unit}"

    @staticmethod
    def _number_text(value: Decimal) -> str:
        return format(value.normalize(), "f")
