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
