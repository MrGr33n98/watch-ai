"""Deterministic local image interpretation fixtures for tests and development."""

from collections.abc import Mapping
from threading import Lock

from app.domain.ingestion.models import InboundMessage
from app.domain.interpretation.models import InterpretationConfidence, InterpretedExercise


class FakeVisionProvider:
    _golden_exercises = {
        "golden-fourier": InterpretedExercise(
            statement=(
                "Parede: k=1,2 W/(m K), A=10 m^2, L=0,20 m, deltaT=40 K. "
                "Calcule Qdot."
            ),
            problem_type="Fourier law",
            confidence=InterpretationConfidence.HIGH,
            needs_review=False,
        ),
        "golden-derivative": InterpretedExercise(
            statement="Derive f(x) = x^2 + 3x.",
            problem_type="derivative",
            confidence=InterpretationConfidence.HIGH,
            needs_review=False,
        ),
        "golden-integral": InterpretedExercise(
            statement="Calculate the definite integral of 2x from 0 to 3.",
            problem_type="definite integral",
            confidence=InterpretationConfidence.HIGH,
            needs_review=False,
        ),
        "golden-unit-conversion": InterpretedExercise(
            statement="Convert 1500 W to kW.",
            problem_type="unit conversion",
            confidence=InterpretationConfidence.HIGH,
            needs_review=False,
        ),
    }
    _ambiguous = InterpretedExercise(
        statement=None,
        problem_type=None,
        confidence=InterpretationConfidence.LOW,
        needs_review=True,
    )

    def __init__(
        self,
        *,
        fixtures: Mapping[str, InterpretedExercise] | None = None,
    ) -> None:
        self._call_count = 0
        self._lock = Lock()
        self._fixtures = {**self._golden_exercises, **(fixtures or {})}

    @property
    def call_count(self) -> int:
        with self._lock:
            return self._call_count

    def interpret(
        self,
        message: InboundMessage,
        *,
        image_bytes: bytes | None = None,
    ) -> InterpretedExercise:
        del image_bytes
        with self._lock:
            self._call_count += 1
        if message.media_sha == "ambiguous":
            return self._ambiguous
        return self._fixtures.get(message.media_sha or "", self._ambiguous)
