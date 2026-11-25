from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.adapters.openrouter.provider import (
    OpenRouterInvalidResponse,
    OpenRouterTimeout,
    OpenRouterVisionProvider,
)
from app.domain.ingestion.models import InboundMessage
from app.domain.interpretation.models import InterpretationConfidence


def make_message() -> InboundMessage:
    return InboundMessage(
        provider="waha",
        provider_message_id="vision-test-1",
        sender_hmac="sender-hmac",
        media_sha="sha256-example",
    )


def make_response(content: str, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code,
        json={"choices": [{"message": {"content": content}}]},
    )


def provider_for(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    max_retries: int = 2,
    sleeps: list[float] | None = None,
) -> OpenRouterVisionProvider:
    client = httpx.Client(
        base_url="https://openrouter.ai/api/v1",
        transport=httpx.MockTransport(handler),
    )
    return OpenRouterVisionProvider(
        api_key="or-test-key",
        model="test/vision-model",
        client=client,
        max_retries=max_retries,
        sleeper=(sleeps.append if sleeps is not None else lambda _: None),
    )


def test_openrouter_sends_private_jpeg_and_parses_typed_json() -> None:
    output = {
        "statement": "Derive f(x) = x^2 + 3x.",
        "problem_type": "derivative",
        "confidence": "high",
        "needs_review": False,
    }
    seen: dict[str, Any] = {}

    def respond(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers["Authorization"]
        seen["payload"] = json.loads(request.content)
        return make_response(json.dumps(output))

    provider = provider_for(respond)
    result = provider.interpret(make_message(), image_bytes=b"private-jpeg")
    provider.close()

    assert result.statement == output["statement"]
    assert result.confidence is InterpretationConfidence.HIGH
    assert seen["authorization"] == "Bearer or-test-key"
    assert seen["payload"]["model"] == "test/vision-model"
    assert seen["payload"]["response_format"] == {"type": "json_object"}
    content = seen["payload"]["messages"][1]["content"]
    assert content[0]["type"] == "text"
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


@pytest.mark.parametrize("content", ["not-json", json.dumps({"statement": "missing fields"})])
def test_openrouter_rejects_invalid_or_incomplete_json(content: str) -> None:
    provider = provider_for(lambda _: make_response(content))

    with pytest.raises(OpenRouterInvalidResponse):
        provider.interpret(make_message(), image_bytes=b"private-jpeg")

    provider.close()


def test_openrouter_retries_429_with_bounded_retry_after() -> None:
    calls = 0
    sleeps: list[float] = []
    content = json.dumps(
        {
            "statement": "Convert 1500 W to kW.",
            "problem_type": "unit conversion",
            "confidence": "high",
            "needs_review": False,
        }
    )

    def respond(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0.25"})
        return make_response(content)

    provider = provider_for(respond, sleeps=sleeps)
    result = provider.interpret(make_message(), image_bytes=b"private-jpeg")
    provider.close()

    assert result.problem_type == "unit conversion"
    assert calls == 2
    assert sleeps == [0.25]


def test_openrouter_timeout_retries_are_bounded() -> None:
    calls = 0
    sleeps: list[float] = []

    def timeout(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("upstream timed out", request=request)

    provider = provider_for(timeout, max_retries=2, sleeps=sleeps)

    with pytest.raises(OpenRouterTimeout):
        provider.interpret(make_message(), image_bytes=b"private-jpeg")

    provider.close()
    assert calls == 3
    assert sleeps == [0.1, 0.2]


def test_openrouter_parses_structured_math_extraction_payload() -> None:
    output = {
        "statement": "Parede: k=1,2 W/(m K), A=10 m^2, deltaT=40 K, L=0,20 m.",
        "problem_type": "Fourier law",
        "confidence": "high",
        "needs_review": False,
        "operation": "fourier",
        "parameters": {
            "k": {"value": "1,2", "unit": "W/(m K)"},
            "A": {"value": "10", "unit": "m^2"},
            "deltaT": {"value": "40", "unit": "K"},
            "L": {"value": "0,20", "unit": "m"},
        },
    }
    provider = provider_for(lambda _: make_response(json.dumps(output)))
    result = provider.interpret(make_message(), image_bytes=b"private-jpeg")
    provider.close()

    assert result.operation == "fourier"
    assert result.parameters["k"].value == "1,2"
    assert result.parameters["k"].unit == "W/(m K)"


def test_openrouter_parses_markdown_fenced_json_object() -> None:
    payload_json = json.dumps(
        {
            "statement": "2+2",
            "problem_type": "simplify",
            "confidence": "high",
            "needs_review": False,
            "operation": "simplify",
            "expression": "2 + 2",
        }
    )
    fenced = f"```json\n{payload_json}\n```"
    provider = provider_for(lambda _: make_response(fenced))
    result = provider.interpret(make_message(), image_bytes=b"private-jpeg")
    provider.close()

    assert result.statement == "2+2"
    assert result.operation == "simplify"
    assert result.expression == "2 + 2"


def test_openrouter_parses_agent_solution_steps() -> None:
    output = {
        "statement": "Derive f(x) = (3x^2 + 2)^5",
        "problem_type": "calculus",
        "confidence": "high",
        "needs_review": False,
        "final_answer": "30x(3x^2 + 2)^4",
        "units": None,
        "steps": [
            {
                "ordinal": 1,
                "kind": "identify",
                "title": "Regra da Cadeia",
                "plain_text": "Definir u = 3x^2 + 2 e f(u) = u^5",
                "latex": r"u = 3x^2 + 2,\quad f(u) = u^5",
            },
            {
                "ordinal": 2,
                "kind": "calculation",
                "title": "Derivada Interna",
                "plain_text": "du/dx = 6x",
                "latex": r"\frac{du}{dx} = 6x",
            },
            {
                "ordinal": 3,
                "kind": "result",
                "title": "Resultado",
                "plain_text": "f'(x) = 30x(3x^2 + 2)^4",
                "latex": r"f'(x) = 30x(3x^2 + 2)^4",
            },
        ],
    }
    provider = provider_for(lambda _: make_response(json.dumps(output)))
    result = provider.interpret(make_message(), image_bytes=b"private-jpeg")
    provider.close()

    assert result.final_answer == "30x(3x^2 + 2)^4"
    assert len(result.solution_steps) == 3
    assert result.solution_steps[0].title == "Regra da Cadeia"
    assert result.solution_steps[1].latex == r"\frac{du}{dx} = 6x"
    assert result.solution_steps[2].kind == "result"


def test_openrouter_parses_document_manifest() -> None:
    output = {
        "document_id": "exam-2026-01",
        "detected_questions": 3,
        "has_shared_figures": True,
        "has_shared_tables": False,
        "questions": [
            {
                "source_number": "Questão 1",
                "ordinal": 1,
                "statement": "Calcule a vazão mássica.",
                "subitems": ["a) Regime laminar", "b) Regime turbulento"],
                "figure_references": ["Figura 1 - Esquema da tubulação"],
                "table_references": [],
            },
            {
                "source_number": "Questão 2",
                "ordinal": 2,
                "statement": "Determine a perda de carga.",
                "subitems": [],
                "figure_references": ["Figura 1 - Esquema da tubulação"],
                "table_references": [],
            },
            {
                "source_number": "3",
                "ordinal": 3,
                "statement": "Calcule a eficiência da bomba.",
                "subitems": [],
                "figure_references": [],
                "table_references": [],
            },
        ],
    }
    provider = provider_for(lambda _: make_response(json.dumps(output)))
    manifest = provider.interpret_document_manifest(b"fake-sheet-jpeg", document_id="exam-2026-01")
    provider.close()

    assert manifest.document_id == "exam-2026-01"
    assert manifest.detected_questions == 3
    assert manifest.has_shared_figures is True
    assert len(manifest.questions) == 3
    assert manifest.questions[0].source_number == "Questão 1"
    assert manifest.questions[0].subitems == ("a) Regime laminar", "b) Regime turbulento")
    assert manifest.questions[1].figure_references == ("Figura 1 - Esquema da tubulação",)
    assert manifest.questions[2].ordinal == 3


