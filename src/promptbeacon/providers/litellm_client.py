"""LiteLLM-based client for multi-provider LLM access."""

from __future__ import annotations

import time
from typing import Any

import litellm
from litellm import acompletion, completion
from litellm.exceptions import (
    AuthenticationError,
    RateLimitError,
    APIError,
)

from promptbeacon.core.config import Provider, get_api_key, has_api_key
from promptbeacon.core.exceptions import (
    ProviderAPIError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
)
from promptbeacon.providers.base import BaseLLMClient, LLMResponse


# Model mapping for each provider
PROVIDER_MODELS: dict[Provider, str] = {
    Provider.OPENAI: "gpt-4o-mini",
    Provider.ANTHROPIC: "claude-3-haiku-20240307",
    Provider.GOOGLE: "gemini/gemini-1.5-flash",
}

# LiteLLM model prefixes
LITELLM_MODEL_MAP: dict[Provider, str] = {
    Provider.OPENAI: "",  # OpenAI models don't need prefix
    Provider.ANTHROPIC: "",  # Anthropic models don't need prefix
    Provider.GOOGLE: "gemini/",  # Google models need gemini/ prefix
}


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
            model: Override the default model for this provider.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries.
        """
        self.provider = provider
        self._model = model or PROVIDER_MODELS.get(provider, "gpt-4o-mini")
        self.timeout = timeout
        self.max_retries = max_retries

        # Configure litellm
        litellm.drop_params = True  # Ignore unsupported params

    @property
    def provider_name(self) -> str:
        return self.provider.value

    @property
    def model(self) -> str:
        """Get the model name with proper prefix for LiteLLM."""
        prefix = LITELLM_MODEL_MAP.get(self.provider, "")
        if self._model.startswith(prefix):
            return self._model
        return f"{prefix}{self._model}"

    def is_available(self) -> bool:
        """Check if the provider is available."""
        return has_api_key(self.provider)

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
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.
            **kwargs: Additional parameters.

        Returns:
            LLMResponse with the completion.
        """
        use_model = model or self.model
        start_time = time.time()

        try:
            response = await acompletion(
                model=use_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout,
                num_retries=self.max_retries,
                **kwargs,
            )

            latency_ms = (time.time() - start_time) * 1000

            # Extract content
            content = response.choices[0].message.content or ""

            # Calculate cost if available
            cost_usd = None
            if hasattr(response, "usage") and response.usage:
                try:
                    cost_usd = litellm.completion_cost(completion_response=response)
                except Exception:
                    pass

            # Extract usage
            usage = None
            if hasattr(response, "usage") and response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return LLMResponse(
                content=content,
                model=use_model,
                provider=self.provider_name,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                usage=usage,
                raw_response=response,
            )

        except AuthenticationError as e:
            raise ProviderAuthenticationError(
                f"Authentication failed for {self.provider_name}: {e}"
            ) from e
        except RateLimitError as e:
            raise ProviderRateLimitError(
                f"Rate limit exceeded for {self.provider_name}: {e}"
            ) from e
        except APIError as e:
            raise ProviderAPIError(
                f"API error from {self.provider_name}: {e}",
                status_code=getattr(e, "status_code", None),
            ) from e
        except Exception as e:
            raise ProviderAPIError(
                f"Unexpected error from {self.provider_name}: {e}"
            ) from e

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
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.
            **kwargs: Additional parameters.

        Returns:
            LLMResponse with the completion.
        """
        use_model = model or self.model
        start_time = time.time()

        try:
            response = completion(
                model=use_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout,
                num_retries=self.max_retries,
                **kwargs,
            )

            latency_ms = (time.time() - start_time) * 1000

            # Extract content
            content = response.choices[0].message.content or ""

            # Calculate cost if available
            cost_usd = None
            if hasattr(response, "usage") and response.usage:
                try:
                    cost_usd = litellm.completion_cost(completion_response=response)
                except Exception:
                    pass

            # Extract usage
            usage = None
            if hasattr(response, "usage") and response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return LLMResponse(
                content=content,
                model=use_model,
                provider=self.provider_name,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                usage=usage,
                raw_response=response,
            )

        except AuthenticationError as e:
            raise ProviderAuthenticationError(
                f"Authentication failed for {self.provider_name}: {e}"
            ) from e
        except RateLimitError as e:
            raise ProviderRateLimitError(
                f"Rate limit exceeded for {self.provider_name}: {e}"
            ) from e
        except APIError as e:
            raise ProviderAPIError(
                f"API error from {self.provider_name}: {e}",
                status_code=getattr(e, "status_code", None),
            ) from e
        except Exception as e:
            raise ProviderAPIError(
                f"Unexpected error from {self.provider_name}: {e}"
            ) from e


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
    """Get a list of providers with configured API keys.

    Returns:
        List of available providers.
    """
    return [p for p in Provider if has_api_key(p)]
