"""The agent defines the measurement: custom prompts, aliases and stability runs,
through the builder, the MCP scan tools and the CLI. No real requests."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from promptbeacon import Beacon, mcp_server
from promptbeacon.builder import configure_beacon
from promptbeacon.cli.main import app
from promptbeacon.projects import HttpResponse

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "projects"

QUESTIONS = [
    "Which Python library should I use to call a REST API?",
    "What do you recommend for async HTTP requests in Python?",
    "Best way to download files in Python?",
]


def run(coro):
    return asyncio.run(coro)


class TestPromptValidation:
    @pytest.mark.parametrize(
        ("prompts", "message"),
        [
            ([], "at least one prompt"),
            (["  "], "empty"),
            (["Best {category}?", "Best {category}?"], "duplicate"),
            (["Best {tool} for {category}?"], r"\{category\}"),
            (['Return JSON like {"a": 1}'], r"\{category\}"),
            (["Best {category!r}?"], r"\{category\}"),
        ],
    )
    def test_bad_prompts_are_rejected(self, prompts, message):
        with pytest.raises(ValueError, match=message):
            Beacon("httpx").with_prompts(prompts)

    def test_literal_braces_can_be_doubled(self):
        beacon = Beacon("httpx").with_prompts(['Answer as JSON, e.g. {{"pick": "x"}}'])
        assert beacon._get_prompts() == ['Answer as JSON, e.g. {"pick": "x"}']

    def test_prompts_are_stripped(self):
        beacon = Beacon("httpx").with_prompts(["  Best client?  "])
        assert beacon._get_prompts() == ["Best client?"]

    def test_fixed_prompts_are_asked_once_whatever_the_categories(self):
        beacon = (
            Beacon("httpx").with_categories("http client", "rest client")
        ).with_prompts(QUESTIONS)
        assert beacon._get_prompts() == QUESTIONS

    def test_category_prompts_are_asked_per_category(self):
        beacon = (
            Beacon("httpx").with_categories("http client", "rest client")
        ).with_prompts(["Best {category}?"])
        assert beacon._get_prompts() == ["Best http client?", "Best rest client?"]


class TestBuilder:
    def test_prompts_aliases_and_stability(self):
        beacon = configure_beacon(
            "httpx",
            prompts=QUESTIONS,
            aliases=["python-httpx", "HTTPX"],  # HTTPX is the brand, any case
            stability_runs=3,
            demo=True,
        )
        assert beacon._get_prompts() == QUESTIONS
        assert beacon.config.brand_aliases == ["python-httpx"]
        assert beacon.stability_runs == 3

    def test_aliases_are_cleaned(self):
        beacon = configure_beacon(
            "httpx", aliases=[" python-httpx ", "HTTPX", "PYTHON-HTTPX", ""]
        )
        assert beacon.config.brand_aliases == ["python-httpx"]

    def test_prompts_and_a_prompt_count_conflict(self):
        with pytest.raises(ValueError, match="prompt count"):
            configure_beacon("httpx", prompts=QUESTIONS, prompt_count=5)

    @pytest.mark.parametrize("runs", [1, -2])
    def test_stability_needs_two_runs(self, runs):
        with pytest.raises(ValueError, match="at least 2"):
            configure_beacon("httpx", stability_runs=runs)

    def test_zero_or_none_means_a_single_scan(self):
        assert configure_beacon("httpx", stability_runs=0).stability_runs is None
        assert configure_beacon("httpx").stability_runs is None

    def test_estimate_counts_custom_prompts_and_runs(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
        beacon = configure_beacon(
            "httpx", prompts=QUESTIONS, stability_runs=4, providers=["openai"]
        )
        estimate = beacon.estimate_cost()
        assert estimate.answers == len(QUESTIONS) * 4


class TestMcp:
    def test_scan_with_custom_prompts_aliases_and_stability(self):
        result = run(
            mcp_server.scan(
                "httpx", custom_prompts=QUESTIONS, aliases=["HTTPX"],
                competitors=["requests"], stability_runs=2, demo=True,
            )
        )  # fmt: skip
        assert result["prompts"] == len(QUESTIONS)
        assert result["prompt_strategy"] == "custom"
        assert result["stability_score"] is not None
        assert result["stability"]["runs"] == 2

    def test_estimate_takes_the_same_measurement(self):
        result = run(
            mcp_server.estimate("httpx", custom_prompts=QUESTIONS, stability_runs=3)
        )
        assert result["answers"] == len(QUESTIONS) * 3

    def test_project_scan_accepts_aliases_and_prompts(self):
        pypi = (FIXTURES / "pypi_httpx.json").read_text(encoding="utf-8")

        def http(url, _headers):
            if "pypi.org" in url:
                return HttpResponse(200, pypi)
            return HttpResponse(404, "")

        with patch("promptbeacon.projects.sources.default_http_get", new=http):
            result = run(
                mcp_server.project_scan(
                    "pypi:httpx", custom_prompts=QUESTIONS[:2],
                    aliases=["python-httpx"], demo=True,
                )
            )  # fmt: skip
        assert result["prompts"] == 2
        assert result["prompt_strategy"] == "custom"

    def test_invalid_prompts_are_a_clear_error(self):
        with pytest.raises(ValueError, match="duplicate"):
            run(mcp_server.scan("httpx", custom_prompts=["a?", "a?"], demo=True))

    def test_stability_bounds(self):
        with pytest.raises(ValueError, match="stability_runs"):
            run(mcp_server.scan("httpx", custom_prompts=QUESTIONS, stability_runs=21))


class TestCli:
    def test_prompt_file_alias_and_stability(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPTBEACON_HOME", str(tmp_path))
        prompt_file = tmp_path / "prompts.txt"
        prompt_file.write_text(
            "# questions developers ask\n\n" + "\n".join(QUESTIONS[:2]) + "\n",
            encoding="utf-8",
        )
        result = CliRunner().invoke(
            app,
            [
                "scan", "httpx", "--demo", "--prompt-file", str(prompt_file),
                "--prompt", QUESTIONS[2], "--alias", "HTTPX", "-r", "2",
                "-f", "json",
            ],
        )  # fmt: skip
        assert result.exit_code == 0, result.output
        data = json.loads(result.stdout)
        prompts = [r["prompt"] for r in data["provider_results"]]
        assert prompts == [QUESTIONS[2], *QUESTIONS[:2]]  # --prompt, then the file
        assert data["prompt_strategy"] == "custom"
        assert data["stability"]["runs"] == 2

    def test_estimate_with_prompts(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
        result = CliRunner().invoke(
            app,
            [
                "scan", "httpx", "-p", "openai", "--prompt", QUESTIONS[0],
                "--prompt", QUESTIONS[1], "--estimate", "-f", "json",
            ],
        )  # fmt: skip
        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout)["answers"] == 2

    def test_missing_prompt_file(self, tmp_path):
        result = CliRunner().invoke(
            app,
            ["scan", "httpx", "--demo", "--prompt-file", str(tmp_path / "nope.txt")],
        )
        assert result.exit_code != 0
        assert "nope.txt" in result.output

    def test_empty_prompt_file(self, tmp_path):
        empty = tmp_path / "empty.txt"
        empty.write_text("# nothing yet\n", encoding="utf-8")
        result = CliRunner().invoke(
            app, ["scan", "httpx", "--demo", "--prompt-file", str(empty)]
        )
        assert result.exit_code == 1
        assert "no prompts" in result.output

    def test_bad_prompt_is_a_clean_error(self):
        result = CliRunner().invoke(
            app, ["scan", "httpx", "--demo", "--prompt", "Best {tool}?"]
        )
        assert result.exit_code == 1
        assert "{category}" in result.output
