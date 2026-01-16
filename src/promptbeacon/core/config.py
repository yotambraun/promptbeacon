"""Configuration management for PromptBeacon."""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Provider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"

    @classmethod
    def all(cls) -> list[Provider]:
        """Return all available providers."""
        return list(cls)


class ModelConfig(BaseModel):
    """Configuration for a specific model."""

    provider: Provider
    model_name: str
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=32768)


# Default models for each provider
DEFAULT_MODELS: dict[Provider, str] = {
    Provider.OPENAI: "gpt-4o-mini",
    Provider.ANTHROPIC: "claude-3-haiku-20240307",
    Provider.GOOGLE: "gemini-1.5-flash",
}


class BeaconConfig(BaseModel):
    """Configuration for a Beacon instance."""

    brand: str = Field(..., min_length=1, description="The brand to monitor")
    competitors: list[str] = Field(default_factory=list, description="Competitor brands")
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
    timeout: float = Field(default=30.0, ge=1.0, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10)
    concurrent_requests: int = Field(default=5, ge=1, le=50)

    @field_validator("brand", "competitors", mode="before")
    @classmethod
    def strip_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        if isinstance(v, list):
            return [s.strip() if isinstance(s, str) else s for s in v]
        return v

    def get_model_for_provider(self, provider: Provider) -> str:
        """Get the default model name for a provider."""
        return DEFAULT_MODELS.get(provider, "gpt-4o-mini")

    def get_storage_path(self) -> Path:
        """Get the storage path, using default if not set."""
        if self.storage_path:
            return self.storage_path
        return get_default_storage_path()


def get_default_storage_path() -> Path:
    """Get the default storage path for PromptBeacon data."""
    home = Path.home()
    data_dir = home / ".promptbeacon"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "data.db"


def get_api_key(provider: Provider) -> str | None:
    """Get the API key for a provider from environment variables."""
    env_vars = {
        Provider.OPENAI: "OPENAI_API_KEY",
        Provider.ANTHROPIC: "ANTHROPIC_API_KEY",
        Provider.GOOGLE: "GOOGLE_API_KEY",
    }
    env_var = env_vars.get(provider)
    if env_var:
        return os.environ.get(env_var)
    return None


def has_api_key(provider: Provider) -> bool:
    """Check if an API key is available for a provider."""
    return get_api_key(provider) is not None
