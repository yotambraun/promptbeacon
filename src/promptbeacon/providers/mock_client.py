"""A keyless mock LLM client for demo mode and offline testing.

``MockLLMClient`` satisfies the same :class:`BaseLLMClient` contract as the real
LiteLLM client, so the entire scan pipeline (extraction, scoring, Share of Voice,
stability) runs unchanged — but it returns deterministic canned responses with
**no API calls and no keys**. This powers ``Beacon(...).demo()`` and is ideal for
CI smoke checks and reproducible tests.
"""

from __future__ import annotations

from typing import Any

from promptbeacon.core.config import DEFAULT_MODELS, Provider
from promptbeacon.providers.base import BaseLLMClient, LLMResponse
from promptbeacon.providers.fixtures import build_demo_response


class MockLLMClient(BaseLLMClient):
    """Offline client returning realistic canned responses (no API key needed)."""

    def __init__(
        self,
        provider: Provider,
        brand: str,
        competitors: list[str] | None = None,
        variation: int = 0,
        model: str | None = None,
    ):
        """Initialize the mock client.

        Args:
            provider: The provider being simulated (for realistic labelling).
            brand: The target brand to weave into responses.
            competitors: Competitor brands to weave into responses.
            variation: Seed that varies responses across stability runs.
            model: Override the simulated model name.
        """
        self.provider = provider
        self._brand = brand
        self._competitors = competitors or []
        self._variation = variation
        self._model = model or DEFAULT_MODELS.get(provider, "gpt-4o-mini")

    @property
    def provider_name(self) -> str:
        return self.provider.value

    @property
    def model(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return True

    def _build(self, prompt: str) -> LLMResponse:
        content = build_demo_response(
            prompt, self._brand, self._competitors, variation=self._variation
        )
        # Deterministic, realistic-looking latency (200-900ms); zero cost.
        latency_ms = 200.0 + (hash((prompt, self._variation)) % 700)
        return LLMResponse(
            content=content,
            model=self._model,
            provider=self.provider.value,
            latency_ms=float(abs(latency_ms)),
            cost_usd=0.0,
            usage=None,
        )

    async def complete(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> LLMResponse:
        # Canned responses ignore sampling params (kept for interface parity).
        _ = (model, temperature, max_tokens, kwargs)
        return self._build(prompt)

    def complete_sync(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> LLMResponse:
        _ = (model, temperature, max_tokens, kwargs)
        return self._build(prompt)
