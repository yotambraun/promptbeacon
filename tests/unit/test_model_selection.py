"""Model choice: one source of defaults, with_models(), env vars, CLI, MCP, LiteLLM."""

from __future__ import annotations

import asyncio
import json
import logging
from types import SimpleNamespace
from typing import Any

import pytest
from typer.testing import CliRunner

from promptbeacon import Beacon, Provider
from promptbeacon.cli.main import app
from promptbeacon.core.config import (
    DEFAULT_MODELS,
    BeaconConfig,
    get_api_key,
    model_env_var,
    parse_model_overrides,
    resolve_model,
)
from promptbeacon.core.exceptions import ConfigurationError
from promptbeacon.protocol import ScanProtocol, build_beacon
from promptbeacon.providers import grounding, litellm_client
from promptbeacon.providers.litellm_client import (
    LiteLLMClient,
    get_available_providers,
    load_litellm,
)
from promptbeacon.providers.mock_client import MockLLMClient

runner = CliRunner()
KEY_VARS = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "MISTRAL_API_KEY",
    "COHERE_API_KEY",
    "PERPLEXITY_API_KEY",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in KEY_VARS:
        monkeypatch.delenv(var, raising=False)
    for provider in Provider:
        monkeypatch.delenv(model_env_var(provider), raising=False)


def _models(report) -> set[tuple[str, str]]:
    return {(r.provider, r.model) for r in report.provider_results}


# --- one source of truth ---------------------------------------------------------


def test_every_hosted_provider_has_a_default_model():
    assert set(DEFAULT_MODELS) == set(Provider.all())
    assert Provider.LITELLM not in DEFAULT_MODELS
    assert Provider.LITELLM not in Provider.all()


def test_clients_use_the_shared_defaults():
    assert not hasattr(litellm_client, "PROVIDER_MODELS")
    for provider, model in DEFAULT_MODELS.items():
        assert LiteLLMClient(provider).model.endswith(model)
        assert MockLLMClient(provider, brand="x").model == model
        gclient = grounding.get_grounded_client(provider)
        if gclient is not None:
            assert gclient._model == model  # type: ignore[attr-defined]


def test_default_models_are_priced_by_litellm():
    litellm = load_litellm()
    for provider, model in DEFAULT_MODELS.items():
        routed = LiteLLMClient(provider).model
        assert routed in litellm.model_cost or model in litellm.model_cost, routed


# --- resolution order --------------------------------------------------------------


def test_resolve_model_precedence(monkeypatch):
    assert resolve_model(Provider.OPENAI) == DEFAULT_MODELS[Provider.OPENAI]
    monkeypatch.setenv("PROMPTBEACON_OPENAI_MODEL", "gpt-6-sol")
    assert resolve_model(Provider.OPENAI) == "gpt-6-sol"
    assert resolve_model(Provider.OPENAI, {Provider.OPENAI: "gpt-6-astra"}) == (
        "gpt-6-astra"
    )
    assert resolve_model(Provider.LITELLM) is None


def test_parse_model_overrides_forms():
    assert parse_model_overrides({"OpenAI": "gpt-6-sol"}) == {
        Provider.OPENAI: "gpt-6-sol"
    }
    assert parse_model_overrides(["litellm=ollama/llama3.2"]) == {
        Provider.LITELLM: "ollama/llama3.2"
    }
    with pytest.raises(ValueError, match="provider=model_id"):
        parse_model_overrides(["gpt-6-sol"])
    with pytest.raises(ValueError, match="Invalid provider"):
        parse_model_overrides({"openia": "x"})
    with pytest.raises(ValueError, match="Empty model"):
        parse_model_overrides(["openai= "])


def test_config_model_lookup_uses_overrides():
    config = BeaconConfig(brand="x", models={Provider.GOOGLE: "gemini-3.8-flash"})
    assert config.get_model_for_provider(Provider.GOOGLE) == "gemini-3.8-flash"
    assert config.get_model_for_provider(Provider.OPENAI) == "gpt-6-luna"


# --- Beacon.with_models -----------------------------------------------------------


def test_with_models_sets_model_and_providers():
    report = (
        Beacon("httpx")
        .demo()
        .with_category("python http client")
        .with_models({"anthropic": "claude-sonnet-5-5"}, google="gemini-3.8-flash")
        .scan()
    )
    assert _models(report) == {
        ("anthropic", "claude-sonnet-5-5"),
        ("google", "gemini-3.8-flash"),
    }


def test_with_models_merges_calls():
    beacon = Beacon("x").with_models(openai="a").with_models(anthropic="b")
    assert beacon.config.models == {Provider.OPENAI: "a", Provider.ANTHROPIC: "b"}


def test_explicit_providers_win_and_unused_models_are_reported(caplog):
    beacon = (
        Beacon("httpx")
        .demo()
        .with_category("python http client")
        .with_providers(Provider.OPENAI)
        .with_models(openai="gpt-6-sol", anthropic="claude-sonnet-5-5")
    )
    with caplog.at_level(logging.WARNING, logger="promptbeacon.beacon"):
        report = beacon.scan()
    assert _models(report) == {("openai", "gpt-6-sol")}
    assert "anthropic" in caplog.text


def test_env_var_model_is_used(monkeypatch):
    monkeypatch.setenv("PROMPTBEACON_OPENAI_MODEL", "gpt-6.1-terra")
    report = Beacon("httpx").demo().with_category("python http client").scan()
    assert _models(report) == {("openai", "gpt-6.1-terra")}


def test_with_models_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Invalid provider"):
        Beacon("x").with_models(openia="gpt-6-luna")


# --- live path through LiteLLM (network replaced by a fake) ------------------------


class _FakeCompletion:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="httpx is good"))],
            usage=None,
        )


@pytest.fixture
def fake_completion(monkeypatch):
    fake = _FakeCompletion()
    monkeypatch.setattr(load_litellm(), "acompletion", fake)
    return fake


def _complete(client: LiteLLMClient, **kwargs: Any):
    return asyncio.run(client.complete("best python http client?", **kwargs))


def test_anthropic_requests_never_send_temperature(fake_completion, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    _complete(LiteLLMClient(Provider.ANTHROPIC), temperature=0.7)
    _complete(LiteLLMClient(Provider.LITELLM, model="openrouter/anthropic/claude-x"))
    assert all("temperature" not in call for call in fake_completion.calls)
    assert fake_completion.calls[0]["model"] == "claude-haiku-5-5"
    roles = [m["role"] for m in fake_completion.calls[0]["messages"]]
    assert roles == ["user"]  # no assistant prefill


def test_other_providers_send_temperature(fake_completion, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    _complete(LiteLLMClient(Provider.OPENAI), temperature=0.4)
    assert fake_completion.calls[0]["temperature"] == 0.4
    assert fake_completion.calls[0]["api_key"] == "test-key"


def test_litellm_slot_passes_the_model_through(fake_completion):
    _complete(LiteLLMClient(Provider.LITELLM, model="ollama/llama3.2"))
    call = fake_completion.calls[0]
    assert call["model"] == "ollama/llama3.2"
    assert "api_key" not in call


def test_litellm_slot_without_model_is_a_clear_error():
    with pytest.raises(ConfigurationError, match="ollama/llama3.2"):
        LiteLLMClient(Provider.LITELLM)


def test_local_ollama_scan_needs_no_api_key(fake_completion):
    report = (
        Beacon("httpx")
        .with_category("python http client")
        .with_prompt_count(2)
        .with_models(litellm="ollama/llama3.2")
        .scan()
    )
    assert _models(report) == {("litellm", "ollama/llama3.2")}
    assert report.measurement_tier == "base_model"
    assert len(fake_completion.calls) == 2


def test_litellm_provider_without_model_explains_how_to_set_one():
    beacon = Beacon("x").with_category("y").with_providers(Provider.LITELLM)
    with pytest.raises(ConfigurationError, match="PROMPTBEACON_LITELLM_MODEL"):
        beacon.scan()


def test_google_models_get_the_gemini_prefix_once(fake_completion, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
    _complete(LiteLLMClient(Provider.GOOGLE))
    _complete(LiteLLMClient(Provider.GOOGLE, model="gemini/gemini-3.8-flash"))
    assert [c["model"] for c in fake_completion.calls] == [
        "gemini/gemini-3.5-flash-lite",
        "gemini/gemini-3.8-flash",
    ]
    assert all(c["api_key"] == "gem-key" for c in fake_completion.calls)


def test_grounded_clients_get_native_model_ids():
    gclient = grounding.get_grounded_client(
        Provider.GOOGLE, model="gemini/gemini-3.8-flash"
    )
    assert gclient is not None
    assert gclient._model == "gemini-3.8-flash"  # type: ignore[attr-defined]
    assert grounding.get_grounded_client(Provider.LITELLM) is None


# --- GEMINI_API_KEY ------------------------------------------------------------------


def test_gemini_api_key_is_accepted(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gem")
    assert get_api_key(Provider.GOOGLE) == "gem"
    assert Provider.GOOGLE in get_available_providers()
    monkeypatch.setenv("GOOGLE_API_KEY", "goog")
    assert get_api_key(Provider.GOOGLE) == "goog"  # GOOGLE_API_KEY wins


# --- CLI, protocol, MCP, pytest plugin ----------------------------------------------


def test_cli_model_option():
    result = runner.invoke(
        app,
        [
            "scan", "httpx", "-t", "python http client", "--demo", "-f", "json",
            "-m", "anthropic=claude-sonnet-5-5", "--model", "openai=gpt-6-sol",
        ],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    models = {(r["provider"], r["model"]) for r in report["provider_results"]}
    assert models == {("anthropic", "claude-sonnet-5-5"), ("openai", "gpt-6-sol")}


def test_cli_rejects_malformed_model_option():
    result = runner.invoke(app, ["scan", "httpx", "-t", "x", "--demo", "-m", "gpt"])
    assert result.exit_code == 1
    assert "provider=model_id" in result.output


def test_cli_help_documents_models():
    result = runner.invoke(app, ["scan", "--help"])
    assert "--model" in result.output
    assert "ollama" in result.output


def test_cli_providers_lists_models_and_litellm(monkeypatch):
    monkeypatch.setenv("PROMPTBEACON_LITELLM_MODEL", "ollama/llama3.2")
    result = runner.invoke(app, ["providers"], env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert "litellm" in result.output
    assert "ollama/llama3.2" in result.output
    assert "GEMINI_API_KEY" in result.output
    assert DEFAULT_MODELS[Provider.OPENAI] in result.output


def test_protocol_pins_models():
    protocol = ScanProtocol(
        brand="httpx",
        categories=["python http client"],
        models={"openai": "gpt-6-sol"},
    )
    report = build_beacon(protocol).demo().scan()
    assert _models(report) == {("openai", "gpt-6-sol")}


def test_mcp_scan_accepts_models():
    from promptbeacon import mcp_server

    result = asyncio.run(
        mcp_server.scan(
            "httpx",
            category="python http client",
            models={"anthropic": "claude-sonnet-5-5"},
            demo=True,
        )
    )
    assert result["models"] == ["anthropic/claude-sonnet-5-5"]


def test_mcp_local_model_counts_as_live():
    from promptbeacon import mcp_server

    assert mcp_server._resolve_demo(None, {"litellm": "ollama/llama3.2"}) == (
        False,
        None,
    )
    assert mcp_server.providers()["models"]["openai"] == "gpt-6-luna"


def test_pytest_plugin_factory_accepts_models():
    from promptbeacon.pytest_plugin import _build_beacon

    beacon = _build_beacon(
        "httpx",
        {"categories": ["python http client"], "models": {"openai": "gpt-6-sol"}},
        demo=True,
    )
    assert _models(beacon.scan()) == {("openai", "gpt-6-sol")}
