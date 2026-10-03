"""Grounded scans must report a real cost estimate — never a silent $0/None."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from promptbeacon import Beacon, Provider
from promptbeacon.providers import grounding
from promptbeacon.providers.grounding import (
    AnthropicGroundedClient,
    GeminiGroundedClient,
    GroundedResponse,
    OpenAIGroundedClient,
    PerplexityGroundedClient,
    estimate_grounded_cost,
)


def _litellm_cost(model: str, provider: str, inp: int, out: int) -> float:
    import litellm

    p, c = litellm.cost_per_token(
        model=model,
        prompt_tokens=inp,
        completion_tokens=out,
        custom_llm_provider=provider,
    )
    return p + c


class _AsyncCall:
    def __init__(self, response):
        self._response = response

    async def create(self, **_kwargs):
        return self._response


def test_anthropic_grounded_cost_includes_tokens_and_searches(monkeypatch):
    import anthropic

    response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="Nike is great.", citations=[])],
        usage=SimpleNamespace(
            input_tokens=1000,
            output_tokens=500,
            server_tool_use=SimpleNamespace(web_search_requests=2),
        ),
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(
        anthropic,
        "AsyncAnthropic",
        lambda **_: SimpleNamespace(messages=_AsyncCall(response)),
    )
    import asyncio

    resp = asyncio.run(AnthropicGroundedClient().complete_grounded("best shoes?"))
    tokens = _litellm_cost("claude-haiku-4-5", "anthropic", 1000, 500)
    assert resp.cost_usd == pytest.approx(tokens + 2 * 0.01)
    assert resp.search_fees_included is True


def test_openai_grounded_cost_from_usage(monkeypatch):
    import openai

    response = SimpleNamespace(
        output=[SimpleNamespace(type="web_search_call")],
        output_text="Nike.",
        usage=SimpleNamespace(input_tokens=2000, output_tokens=300),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setattr(
        openai,
        "AsyncOpenAI",
        lambda **_: SimpleNamespace(responses=_AsyncCall(response)),
    )
    import asyncio

    resp = asyncio.run(OpenAIGroundedClient().complete_grounded("best shoes?"))
    assert resp.cost_usd is not None and resp.cost_usd > 0
    assert resp.cost_usd >= _litellm_cost("gpt-4o-mini", "openai", 2000, 300)


def test_gemini_grounded_cost_from_usage_metadata(monkeypatch):
    from google import genai

    candidate = SimpleNamespace(
        grounding_metadata=SimpleNamespace(
            grounding_chunks=[
                SimpleNamespace(web=SimpleNamespace(uri="https://www.example.com/a"))
            ],
            grounding_supports=[],
        )
    )
    response = SimpleNamespace(
        text="Nike.",
        candidates=[candidate],
        usage_metadata=SimpleNamespace(
            prompt_token_count=1000, candidates_token_count=1000
        ),
    )

    class _Models:
        async def generate_content(self, **_kwargs):
            return response

    monkeypatch.setenv("GOOGLE_API_KEY", "test")
    monkeypatch.setattr(
        genai,
        "Client",
        lambda **_: SimpleNamespace(aio=SimpleNamespace(models=_Models())),
    )
    import asyncio

    client = GeminiGroundedClient(model="gemini-2.5-flash")
    resp = asyncio.run(client.complete_grounded("best shoes?"))
    assert resp.cost_usd is not None and resp.cost_usd > 0
    # Gemini grounding fees are not in the price map: say so, don't hide it.
    assert resp.search_fees_included is False


def test_perplexity_grounded_cost_from_usage(monkeypatch):
    import openai

    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Nike."))],
        citations=["https://example.com"],
        usage=SimpleNamespace(prompt_tokens=100, completion_tokens=100),
    )
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test")
    monkeypatch.setattr(
        openai,
        "AsyncOpenAI",
        lambda **_: SimpleNamespace(
            chat=SimpleNamespace(completions=_AsyncCall(response))
        ),
    )
    import asyncio

    resp = asyncio.run(PerplexityGroundedClient().complete_grounded("best shoes?"))
    assert resp.cost_usd is not None and resp.cost_usd > 0


def test_unknown_model_cost_is_none_not_zero():
    cost, included = estimate_grounded_cost(
        Provider.OPENAI, "no-such-model-xyz", 100, 100, search_count=1
    )
    assert cost is None
    assert included is False


def test_report_marks_cost_partial_when_some_costs_unknown(monkeypatch):
    responses = iter([0.002, None])

    class _Fake:
        provider = Provider.ANTHROPIC

        def is_available(self):
            return True

        async def complete_grounded(self, _prompt, **_kwargs):
            return GroundedResponse(
                content="Nike is great",
                citations=[],
                model="claude-haiku-4-5",
                provider="anthropic",
                latency_ms=1.0,
                cost_usd=next(responses),
                search_count=1,
                search_fees_included=True,
            )

    monkeypatch.setattr(
        "promptbeacon.beacon.get_available_providers", lambda: [Provider.ANTHROPIC]
    )
    monkeypatch.setattr("promptbeacon.beacon.get_grounded_client", lambda _p: _Fake())
    report = (
        Beacon("Nike")
        .with_category("running shoes")
        .with_providers(Provider.ANTHROPIC)
        .with_grounding()
        .with_prompt_count(2)
        .scan()
    )
    assert report.total_cost_usd == pytest.approx(0.002)
    assert report.cost_status == "partial"


def test_demo_cost_is_reported_as_free_not_unknown():
    report = Beacon("Nike").demo().with_category("running shoes").scan()
    assert report.cost_status == "none"


def test_grounding_module_exposes_search_fee_constant():
    assert pytest.approx(0.01) == grounding.ANTHROPIC_WEB_SEARCH_USD_PER_SEARCH
