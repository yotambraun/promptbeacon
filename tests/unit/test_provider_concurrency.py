"""Providers are queried concurrently; empty API keys count as not configured."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from promptbeacon import Beacon, Provider
from promptbeacon.core.config import get_api_key, has_api_key
from promptbeacon.providers.base import BaseLLMClient, LLMResponse
from promptbeacon.providers.litellm_client import get_available_providers

DELAY = 0.25


class _SlowClient(BaseLLMClient):
    def __init__(self, provider: Provider):
        self.provider = provider

    @property
    def provider_name(self) -> str:
        return self.provider.value

    @property
    def model(self) -> str:
        return "slow"

    def is_available(self) -> bool:
        return True

    async def complete(self, _prompt: str, **_kwargs: Any) -> LLMResponse:
        await asyncio.sleep(DELAY)
        return LLMResponse(
            content="Nike is a great choice.",
            model="slow",
            provider=self.provider.value,
            latency_ms=DELAY * 1000,
        )

    def complete_sync(self, _prompt: str, **_kwargs: Any) -> LLMResponse:
        raise NotImplementedError


def test_providers_run_concurrently_and_keep_order(monkeypatch):
    providers = [Provider.OPENAI, Provider.ANTHROPIC, Provider.GOOGLE]
    beacon = (
        Beacon("Nike")
        .demo()
        .with_category("running shoes")
        .with_providers(*providers)
        .with_prompt_count(1)
    )
    monkeypatch.setattr(
        beacon, "_make_client", lambda provider, **_kw: _SlowClient(provider)
    )
    start = time.perf_counter()
    report = beacon.scan()
    elapsed = time.perf_counter() - start

    # Sequential would take 3 x DELAY; concurrent takes ~1 x DELAY.
    assert elapsed < 2 * DELAY, f"providers ran sequentially ({elapsed:.2f}s)"
    assert [r.provider for r in report.provider_results] == [p.value for p in providers]


def test_empty_api_key_is_treated_as_unset(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
    assert get_api_key(Provider.OPENAI) is None
    assert not has_api_key(Provider.OPENAI)
    assert not has_api_key(Provider.ANTHROPIC)
    assert Provider.OPENAI not in get_available_providers()
