"""LiteLLM-based client for multi-provider LLM access.

LiteLLM is imported lazily, on the first real (non-demo) request: importing it
takes seconds, and the keyless demo, the share renderers and most of the CLI
never need it.
"""

from __future__ import annotations

import contextlib
import logging
import os
import time
from types import ModuleType
from typing import Any

from promptbeacon.core.config import Provider, get_api_key, has_api_key, resolve_model
from promptbeacon.core.exceptions import (
    ConfigurationError,
    ProviderAPIError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
)
from promptbeacon.providers.base import BaseLLMClient, LLMResponse

logger = logging.getLogger(__name__)

# LiteLLM model prefixes. The LITELLM slot takes the user's model string as-is
# (e.g. "ollama/llama3.2", "openrouter/meta-llama/llama-3.3-70b-instruct").
LITELLM_MODEL_MAP: dict[Provider, str] = {
    Provider.OPENAI: "",  # OpenAI models don't need prefix
    Provider.ANTHROPIC: "",  # Anthropic models don't need prefix
    Provider.GOOGLE: "gemini/",  # Google models need gemini/ prefix
    Provider.MISTRAL: "mistral/",
    Provider.COHERE: "cohere/",
    Provider.PERPLEXITY: "perplexity/",
    Provider.LITELLM: "",
}

_COST_MAP_ENV = "LITELLM_LOCAL_MODEL_COST_MAP"
_litellm_module: ModuleType | None = None


def load_litellm() -> ModuleType:
    """Import and configure LiteLLM once, on first use.

    Uses the price map bundled with the installed LiteLLM (no network fetch at
    import, no warning when offline) unless ``LITELLM_LOCAL_MODEL_COST_MAP`` is
    already set; set it to ``False`` to fetch LiteLLM's latest prices.
    """
    global _litellm_module
    if _litellm_module is None:
        os.environ.setdefault(_COST_MAP_ENV, "True")
        import litellm

        litellm.drop_params = True  # drop params a model does not support
        _litellm_module = litellm
    return _litellm_module


def to_litellm_model(provider: Provider, model: str) -> str:
    """Add the LiteLLM routing prefix for a provider (if not already present)."""
    prefix = LITELLM_MODEL_MAP.get(provider, "")
    if not prefix or model.startswith(prefix):
        return model
    return f"{prefix}{model}"


def to_native_model(provider: Provider, model: str) -> str:
    """Strip the LiteLLM routing prefix (for the providers' own SDKs)."""
    prefix = LITELLM_MODEL_MAP.get(provider, "")
    if prefix and model.startswith(prefix):
        return model[len(prefix) :]
    return model


def omits_sampling_params(provider: Provider, model: str) -> bool:
    """Whether ``temperature`` must not be sent.

    Current Claude models reject any non-default ``temperature`` (and the
    Anthropic API rejects sampling parameters on every model from API version
    2026-10-21), so it is never sent to Anthropic, including Claude models
    reached through the LiteLLM slot (e.g. OpenRouter or Bedrock).
    """
    return provider == Provider.ANTHROPIC or "claude" in model.lower()


class LiteLLMClient(BaseLLMClient):
    """LiteLLM-based client supporting multiple providers."""

    def __init__(
        self,
        provider: Provider,
        model: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """Initialize the LiteLLM client.

        Args:
            provider: The LLM provider to use.
            model: Override the model for this provider. Defaults to
                ``PROMPTBEACON_<PROVIDER>_MODEL`` or the built-in default.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries.

        Raises:
            ConfigurationError: For ``Provider.LITELLM`` without a model.
        """
        resolved = model or resolve_model(provider)
        if not resolved:
            raise ConfigurationError(
                f"No model set for provider '{provider.value}'. Pass one with "
                f"--model {provider.value}=<model> (CLI), "
                f'.with_models({{"{provider.value}": "<model>"}}) (Python), or '
                f"set PROMPTBEACON_{provider.value.upper()}_MODEL. "
                'Example: "ollama/llama3.2" for a local Ollama model.'
            )
        self.provider = provider
        self._model = resolved
        self.timeout = timeout
        self.max_retries = max_retries

    @property
    def provider_name(self) -> str:
        return self.provider.value

    @property
    def model(self) -> str:
        """Get the model name with proper prefix for LiteLLM."""
        return to_litellm_model(self.provider, self._model)

    def is_available(self) -> bool:
        """Check if the provider is available."""
        if self.provider == Provider.LITELLM:
            return True  # credentials (if any) are LiteLLM's business
        return has_api_key(self.provider)

    def _request_kwargs(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        extra: dict[str, Any],
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "timeout": self.timeout,
            "num_retries": self.max_retries,
        }
        if not omits_sampling_params(self.provider, model):
            kwargs["temperature"] = temperature
        # Pass the key explicitly so every accepted env var name works (e.g.
        # GEMINI_API_KEY as well as GOOGLE_API_KEY).
        api_key = get_api_key(self.provider)
        if api_key:
            kwargs["api_key"] = api_key
        kwargs.update(extra)
        return kwargs

    def _to_response(
        self, litellm: ModuleType, response: Any, model: str, start_time: float
    ) -> LLMResponse:
        latency_ms = (time.time() - start_time) * 1000
        content = response.choices[0].message.content or ""

        cost_usd = None
        usage = None
        if getattr(response, "usage", None):
            with contextlib.suppress(Exception):
                cost_usd = litellm.completion_cost(completion_response=response)
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return LLMResponse(
            content=content,
            model=model,
            provider=self.provider_name,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            usage=usage,
            raw_response=response,
        )

    def _translate_error(self, litellm: ModuleType, e: Exception) -> Exception:
        """Map LiteLLM exceptions onto PromptBeacon's provider errors."""
        exceptions = litellm.exceptions
        name = self.provider_name
        detail = f"{type(e).__name__}: {e}"
        if isinstance(e, exceptions.AuthenticationError):
            logger.error("Authentication failed for %s: %s", name, detail)
            return ProviderAuthenticationError(
                f"Authentication failed for {name}: {detail}"
            )
        if isinstance(e, exceptions.RateLimitError):
            logger.warning("Rate limit exceeded for %s: %s", name, detail)
            return ProviderRateLimitError(f"Rate limit exceeded for {name}: {detail}")
        if isinstance(e, exceptions.APIError):
            logger.error("API error from %s: %s", name, detail)
            return ProviderAPIError(
                f"API error from {name}: {detail}",
                status_code=getattr(e, "status_code", None),
            )
        logger.error("Unexpected error from %s: %s", name, detail)
        return ProviderAPIError(f"Unexpected error from {name}: {detail}")

    async def complete(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a prompt to the LLM asynchronously.

        Args:
            prompt: The prompt to send.
            model: Override the model for this request.
            temperature: Sampling temperature (not sent to Claude models).
            max_tokens: Maximum tokens in response.
            **kwargs: Additional parameters.

        Returns:
            LLMResponse with the completion.
        """
        litellm = load_litellm()
        use_model = to_litellm_model(self.provider, model) if model else self.model
        start_time = time.time()
        try:
            response = await litellm.acompletion(
                **self._request_kwargs(
                    prompt, use_model, temperature, max_tokens, kwargs
                )
            )
        except Exception as e:
            raise self._translate_error(litellm, e) from e
        return self._to_response(litellm, response, use_model, start_time)

    def complete_sync(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a prompt to the LLM synchronously.

        Args:
            prompt: The prompt to send.
            model: Override the model for this request.
            temperature: Sampling temperature (not sent to Claude models).
            max_tokens: Maximum tokens in response.
            **kwargs: Additional parameters.

        Returns:
            LLMResponse with the completion.
        """
        litellm = load_litellm()
        use_model = to_litellm_model(self.provider, model) if model else self.model
        start_time = time.time()
        try:
            response = litellm.completion(
                **self._request_kwargs(
                    prompt, use_model, temperature, max_tokens, kwargs
                )
            )
        except Exception as e:
            raise self._translate_error(litellm, e) from e
        return self._to_response(litellm, response, use_model, start_time)


def create_client(
    provider: Provider,
    model: str | None = None,
    timeout: float = 30.0,
    max_retries: int = 3,
) -> LiteLLMClient:
    """Factory function to create a LiteLLM client.

    Args:
        provider: The LLM provider.
        model: Optional model override.
        timeout: Request timeout.
        max_retries: Maximum retries.

    Returns:
        Configured LiteLLMClient.
    """
    return LiteLLMClient(
        provider=provider,
        model=model,
        timeout=timeout,
        max_retries=max_retries,
    )


def get_available_providers() -> list[Provider]:
    """Get the hosted providers that have an API key configured.

    ``Provider.LITELLM`` is not listed: it is available whenever a model is set
    for it (see :meth:`promptbeacon.Beacon.with_models`).

    Returns:
        List of available providers.
    """
    return [p for p in Provider.all() if has_api_key(p)]
