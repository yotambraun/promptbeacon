"""Configuration management for PromptBeacon."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from enum import Enum
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

_ENV_LOADED = False


def load_env(dotenv_path: str | Path | None = None, *, override: bool = False) -> None:
    """Load environment variables from a ``.env`` file (idempotent).

    Searches the working directory (and parents) for a ``.env`` file and loads
    keys such as ``OPENAI_API_KEY``, ``ANTHROPIC_API_KEY``, and
    ``TAVILY_API_KEY`` into the environment — **without** overriding values
    already set in the real environment (explicit env wins). Called
    automatically on import so keys "just work" from a ``.env`` file for both
    library and CLI users.
    """
    global _ENV_LOADED
    if _ENV_LOADED and dotenv_path is None:
        return
    load_dotenv(dotenv_path=dotenv_path, override=override)
    if dotenv_path is None:
        _ENV_LOADED = True


# Auto-load .env on import so a .env file populates the environment.
load_env()


class Provider(str, Enum):
    """Supported LLM providers.

    The first six are hosted APIs with a built-in default model and an API key
    environment variable. ``LITELLM`` is a pass-through slot for any model
    string LiteLLM understands (a local Ollama model, OpenRouter, Azure, a
    vLLM server, ...); it has no default model, so it is only used when a
    model is set for it.
    """

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    COHERE = "cohere"
    PERPLEXITY = "perplexity"
    LITELLM = "litellm"

    @classmethod
    def all(cls) -> list[Provider]:
        """Return the built-in hosted providers (everything except ``LITELLM``)."""
        return [p for p in cls if p is not cls.LITELLM]

    @classmethod
    def parse(cls, name: str | Provider) -> Provider:
        """Parse a provider name (case-insensitive).

        Raises:
            ValueError: For an unknown name, listing the valid ones.
        """
        if isinstance(name, Provider):
            return name
        try:
            return cls(str(name).strip().lower())
        except ValueError:
            valid = ", ".join(p.value for p in cls)
            raise ValueError(
                f"Invalid provider: {name}. Choose from: {valid}"
            ) from None


class ModelConfig(BaseModel):
    """Configuration for a specific model."""

    provider: Provider
    model_name: str
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=32768)


# The single source of truth for default models. Each default is the provider's
# low-cost general model, so a 10-prompt scan stays cheap. Verified 2026-11-01:
# every ID is in litellm's bundled price map (litellm>=1.106, used for cost
# estimates) and in the provider's own model documentation, except where noted.
#   openai      gpt-6-luna             developers.openai.com/api/docs/models
#   anthropic   claude-haiku-5-5       platform.claude.com/docs (models overview)
#   google      gemini-3.5-flash-lite  ai.google.dev/gemini-api/docs/models
#   mistral     mistral-small-latest   alias for the current Mistral Small
#                                      (Small 4 per docs.mistral.ai); the alias
#                                      itself is confirmed via litellm's map
#   cohere      command-r7b-12-2024    docs.cohere.com/docs/models ("command-r"
#                                      is deprecated)
#   perplexity  sonar                  docs.perplexity.ai (Sonar requests are
#                                      now served through the Agent API)
# Override per provider with Beacon.with_models(), the CLI's
# --model provider=model_id, or PROMPTBEACON_<PROVIDER>_MODEL.
DEFAULT_MODELS: dict[Provider, str] = {
    Provider.OPENAI: "gpt-6-luna",
    Provider.ANTHROPIC: "claude-haiku-5-5",
    Provider.GOOGLE: "gemini-3.5-flash-lite",
    Provider.MISTRAL: "mistral-small-latest",
    Provider.COHERE: "command-r7b-12-2024",
    Provider.PERPLEXITY: "sonar",
}


def model_env_var(provider: Provider) -> str:
    """Environment variable that overrides a provider's model.

    ``PROMPTBEACON_OPENAI_MODEL``, ``PROMPTBEACON_LITELLM_MODEL``, ...
    """
    return f"PROMPTBEACON_{provider.value.upper()}_MODEL"


def resolve_model(
    provider: Provider, overrides: Mapping[Provider, str] | None = None
) -> str | None:
    """The model to use for a provider.

    Precedence: an explicit override (``Beacon.with_models`` / ``--model``),
    then ``PROMPTBEACON_<PROVIDER>_MODEL``, then :data:`DEFAULT_MODELS`.
    Returns ``None`` only for :attr:`Provider.LITELLM` with no model set.
    """
    if overrides and overrides.get(provider):
        return overrides[provider]
    env_value = os.environ.get(model_env_var(provider), "").strip()
    if env_value:
        return env_value
    return DEFAULT_MODELS.get(provider)


def parse_model_overrides(
    models: Mapping[str, str] | Mapping[Provider, str] | Iterable[str] | None,
) -> dict[Provider, str]:
    """Normalise model overrides to ``{Provider: model_id}``.

    Accepts a mapping (``{"openai": "gpt-6-sol"}``) or ``provider=model_id``
    strings (the CLI and GitHub Action form, e.g. ``"litellm=ollama/llama3.2"``).

    Raises:
        ValueError: For an unknown provider, a missing ``=`` or an empty model.
    """
    if not models:
        return {}
    pairs: list[tuple[str | Provider, str]]
    if isinstance(models, Mapping):
        pairs = list(models.items())
    else:
        pairs = []
        for item in models:
            name, sep, model_id = str(item).partition("=")
            if not sep:
                raise ValueError(
                    f"Invalid model {item!r}: use provider=model_id, "
                    "e.g. openai=gpt-6-luna or litellm=ollama/llama3.2"
                )
            pairs.append((name, model_id))
    parsed: dict[Provider, str] = {}
    for name, model_id in pairs:
        provider = Provider.parse(name)
        model_id = str(model_id).strip()
        if not model_id:
            raise ValueError(f"Empty model id for provider {provider.value!r}")
        parsed[provider] = model_id
    return parsed


class BeaconConfig(BaseModel):
    """Configuration for a Beacon instance."""

    brand: str = Field(..., min_length=1, description="The brand to monitor")
    brand_aliases: list[str] = Field(
        default_factory=list,
        description="Alternative names for the brand (e.g. 'Nike Inc', 'Nike Corporation')",
    )
    competitors: list[str] = Field(
        default_factory=list, description="Competitor brands"
    )
    providers: list[Provider] = Field(
        default_factory=lambda: [Provider.OPENAI],
        description="LLM providers to query",
    )
    categories: list[str] = Field(
        default_factory=lambda: ["general"],
        description="Categories/topics to analyze",
    )
    prompt_count: int = Field(
        default=10, ge=1, le=1000, description="Number of prompts per category"
    )
    storage_path: Path | None = Field(
        default=None, description="Path to DuckDB storage file"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=32768)
    timeout: float = Field(
        default=30.0, ge=1.0, description="Request timeout in seconds"
    )
    max_retries: int = Field(default=3, ge=0, le=10)
    concurrent_requests: int = Field(default=5, ge=1, le=50)
    models: dict[Provider, str] = Field(
        default_factory=dict,
        description="Per-provider model overrides (see resolve_model)",
    )

    @field_validator("brand", "competitors", mode="before")
    @classmethod
    def strip_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        if isinstance(v, list):
            return [s.strip() if isinstance(s, str) else s for s in v]
        return v

    def get_model_for_provider(self, provider: Provider) -> str | None:
        """The model used for a provider (overrides, env var, then default)."""
        return resolve_model(provider, self.models)

    def get_storage_path(self) -> Path:
        """Get the storage path, using default if not set."""
        if self.storage_path:
            return self.storage_path
        return get_default_storage_path()


HOME_ENV_VAR = "PROMPTBEACON_HOME"


def get_promptbeacon_home() -> Path:
    """Directory for PromptBeacon data: ``$PROMPTBEACON_HOME`` or ``~/.promptbeacon``."""
    override = os.environ.get(HOME_ENV_VAR, "").strip()
    return Path(override).expanduser() if override else Path.home() / ".promptbeacon"


def get_default_storage_path() -> Path:
    """Get the default storage path for PromptBeacon data.

    ``$PROMPTBEACON_HOME/data.db`` when the variable is set, otherwise
    ``~/.promptbeacon/data.db``. The CLI saves real scans here by default.
    """
    data_dir = get_promptbeacon_home()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "data.db"


# API key environment variables, in lookup order. Google accepts either name:
# GOOGLE_API_KEY (what PromptBeacon has always read) or GEMINI_API_KEY (what
# Google AI Studio and the Gemini docs use).
API_KEY_ENV_VARS: dict[Provider, tuple[str, ...]] = {
    Provider.OPENAI: ("OPENAI_API_KEY",),
    Provider.ANTHROPIC: ("ANTHROPIC_API_KEY",),
    Provider.GOOGLE: ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    Provider.MISTRAL: ("MISTRAL_API_KEY",),
    Provider.COHERE: ("COHERE_API_KEY",),
    Provider.PERPLEXITY: ("PERPLEXITY_API_KEY",),
}


def get_api_key(provider: Provider) -> str | None:
    """Get the API key for a provider from environment variables.

    ``Provider.LITELLM`` has no key of its own: LiteLLM reads the credentials
    for the routed backend (e.g. ``OPENROUTER_API_KEY``) itself.
    """
    for env_var in API_KEY_ENV_VARS.get(provider, ()):
        # Empty values (e.g. "${VAR:-}" in MCP/CI config) mean "not configured".
        value = os.environ.get(env_var, "").strip()
        if value:
            return value
    return None


def has_api_key(provider: Provider) -> bool:
    """Check if an API key is available for a provider."""
    return get_api_key(provider) is not None


# Tavily powers the funnel's live web search (it is not an LLM provider).
TAVILY_ENV_VAR = "TAVILY_API_KEY"


def get_tavily_api_key() -> str | None:
    """Get the Tavily API key (used by the funnel's live web search), if set."""
    value = os.environ.get(TAVILY_ENV_VAR, "").strip()
    return value or None


def has_tavily_api_key() -> bool:
    """Whether a Tavily API key is configured."""
    return get_tavily_api_key() is not None
