"""Tests for Beacon class."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from promptbeacon.beacon import Beacon, DEFAULT_PROMPTS
from promptbeacon.core.config import Provider
from promptbeacon.core.exceptions import ConfigurationError


class TestBeaconConfiguration:
    """Tests for Beacon configuration."""

    def test_create_beacon(self):
        beacon = Beacon("Test Brand")

        assert beacon.brand == "Test Brand"

    def test_with_competitors(self):
        beacon = Beacon("Test").with_competitors("Comp A", "Comp B")

        assert "Comp A" in beacon.config.competitors
        assert "Comp B" in beacon.config.competitors

    def test_with_competitors_list(self):
        beacon = Beacon("Test").with_competitors(["Comp A", "Comp B"])

        assert "Comp A" in beacon.config.competitors
        assert "Comp B" in beacon.config.competitors

    def test_with_providers(self):
        beacon = Beacon("Test").with_providers(Provider.OPENAI, Provider.ANTHROPIC)

        assert Provider.OPENAI in beacon.config.providers
        assert Provider.ANTHROPIC in beacon.config.providers

    def test_with_categories(self):
        beacon = Beacon("Test").with_categories("shoes", "apparel")

        assert "shoes" in beacon.config.categories
        assert "apparel" in beacon.config.categories

    def test_with_prompt_count(self):
        beacon = Beacon("Test").with_prompt_count(50)

        assert beacon.config.prompt_count == 50

    def test_with_temperature(self):
        beacon = Beacon("Test").with_temperature(0.5)

        assert beacon.config.temperature == 0.5

    def test_with_max_tokens(self):
        beacon = Beacon("Test").with_max_tokens(2048)

        assert beacon.config.max_tokens == 2048

    def test_with_timeout(self):
        beacon = Beacon("Test").with_timeout(60.0)

        assert beacon.config.timeout == 60.0

    def test_fluent_api_chaining(self):
        beacon = (
            Beacon("Test")
            .with_competitors("Comp A")
            .with_providers(Provider.OPENAI)
            .with_categories("category1")
            .with_prompt_count(20)
        )

        assert beacon.brand == "Test"
        assert "Comp A" in beacon.config.competitors
        assert Provider.OPENAI in beacon.config.providers
        assert "category1" in beacon.config.categories
        assert beacon.config.prompt_count == 20

    def test_with_custom_prompts(self):
        custom_prompts = ["What is the best {category}?"]
        beacon = Beacon("Test").with_prompts(custom_prompts)

        prompts = beacon._get_prompts()

        assert len(prompts) > 0
        assert "general" in prompts[0]


class TestBeaconPrompts:
    """Tests for prompt generation."""

    def test_default_prompts(self):
        beacon = Beacon("Test")
        prompts = beacon._get_prompts()

        assert len(prompts) > 0
        # Default category is "general"
        assert any("general" in p for p in prompts)

    def test_prompts_with_multiple_categories(self):
        beacon = Beacon("Test").with_categories("shoes", "apparel")
        prompts = beacon._get_prompts()

        assert any("shoes" in p for p in prompts)
        assert any("apparel" in p for p in prompts)

    def test_prompt_count_limits(self):
        beacon = Beacon("Test").with_prompt_count(3)
        prompts = beacon._get_prompts()

        # Should have 3 prompts for the default "general" category
        assert len(prompts) == 3


class TestBeaconContextManager:
    """Tests for context manager support."""

    def test_context_manager(self):
        with Beacon("Test") as beacon:
            assert beacon.brand == "Test"

    def test_close(self):
        beacon = Beacon("Test")
        beacon.close()  # Should not raise


class TestBeaconStorage:
    """Tests for storage configuration."""

    def test_with_storage(self, tmp_path):
        db_path = tmp_path / "test.db"
        beacon = Beacon("Test").with_storage(db_path)

        assert beacon.config.storage_path == db_path

    def test_get_history_without_storage(self):
        beacon = Beacon("Test")

        with pytest.raises(ConfigurationError):
            beacon.get_history()

    def test_compare_without_storage(self):
        beacon = Beacon("Test")

        with pytest.raises(ConfigurationError):
            beacon.compare_with_previous()
