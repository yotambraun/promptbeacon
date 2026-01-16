"""Base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Response from an LLM provider."""

    content: str
    model: str
    provider: str
    latency_ms: float
    cost_usd: float | None = None
    usage: dict[str, int] | None = None
    raw_response: Any = None


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the provider."""
        pass

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a prompt to the LLM and get a response.

        Args:
            prompt: The prompt to send.
            model: The model to use (provider-specific).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.
            **kwargs: Additional provider-specific parameters.

        Returns:
            LLMResponse with the completion.
        """
        pass

    @abstractmethod
    def complete_sync(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> LLMResponse:
        """Synchronous version of complete.

        Args:
            prompt: The prompt to send.
            model: The model to use (provider-specific).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.
            **kwargs: Additional provider-specific parameters.

        Returns:
            LLMResponse with the completion.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available (API key configured, etc.)."""
        pass
