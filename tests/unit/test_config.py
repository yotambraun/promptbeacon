"""Tests for configuration module."""

import os
import pytest

from promptbeacon.core.config import (
    BeaconConfig,
    Provider,
    get_api_key,
    has_api_key,
    get_default_storage_path,
)


class TestProvider:
    """Tests for Provider enum."""

    def test_all_providers(self):
        all_providers = Provider.all()

        assert Provider.OPENAI in all_providers
        assert Provider.ANTHROPIC in all_providers
        assert Provider.GOOGLE in all_providers

    def test_provider_values(self):
        assert Provider.OPENAI.value == "openai"
        assert Provider.ANTHROPIC.value == "anthropic"
        assert Provider.GOOGLE.value == "google"


class TestBeaconConfig:
    """Tests for BeaconConfig."""

    def test_create_config(self):
        config = BeaconConfig(brand="Test Brand")

        assert config.brand == "Test Brand"
        assert config.competitors == []
        assert config.prompt_count == 10

    def test_strip_brand_name(self):
        config = BeaconConfig(brand="  Test Brand  ")

        assert config.brand == "Test Brand"

    def test_strip_competitors(self):
        config = BeaconConfig(
            brand="Test",
            competitors=["  Competitor A  ", " Competitor B "],
        )

        assert config.competitors == ["Competitor A", "Competitor B"]

    def test_invalid_prompt_count(self):
        with pytest.raises(ValueError):
            BeaconConfig(brand="Test", prompt_count=0)

        with pytest.raises(ValueError):
            BeaconConfig(brand="Test", prompt_count=1001)

    def test_invalid_temperature(self):
        with pytest.raises(ValueError):
            BeaconConfig(brand="Test", temperature=3.0)

    def test_default_providers(self):
        config = BeaconConfig(brand="Test")

        assert Provider.OPENAI in config.providers

    def test_get_model_for_provider(self):
        config = BeaconConfig(brand="Test")

        model = config.get_model_for_provider(Provider.OPENAI)

        assert model is not None
        assert isinstance(model, str)


class TestAPIKeyFunctions:
    """Tests for API key functions."""

    def test_get_api_key_not_set(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        key = get_api_key(Provider.OPENAI)

        assert key is None

    def test_get_api_key_set(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        key = get_api_key(Provider.OPENAI)

        assert key == "test-key"

    def test_has_api_key_false(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        assert has_api_key(Provider.OPENAI) is False

    def test_has_api_key_true(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        assert has_api_key(Provider.OPENAI) is True


class TestStoragePath:
    """Tests for storage path functions."""

    def test_get_default_storage_path(self):
        path = get_default_storage_path()

        assert path is not None
        assert path.name == "data.db"
        assert ".promptbeacon" in str(path)
