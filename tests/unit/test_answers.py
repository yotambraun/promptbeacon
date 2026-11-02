"""Per-answer evidence: answer_rows, the MCP answers tool and `promptbeacon answers`."""

from __future__ import annotations

import csv
import io
import json

import pytest
from typer.testing import CliRunner

from promptbeacon import mcp_server
from promptbeacon.cli.main import app
from promptbeacon.core.schemas import (
    Citation,
    ProviderResult,
    Report,
    VisibilityMetrics,
)
from promptbeacon.extraction.mentions import extract_mentions
from promptbeacon.reporting import answer_rows

ANSWERS = [
    (
        "openai",
        "gpt-6-luna",
        "Best python http client?",
        "Top picks:\n1. requests\n2. httpx: async\nI recommend httpx for new code.",
        ["https://www.python-httpx.org/", "https://www.python-httpx.org/"],
    ),
    (
        "openai",
        "gpt-6-luna",
        "Async http client for python?",
        "aiohttp is the usual choice for asyncio servers. " + "Long detail. " * 60,
        [],
    ),
    (
        "anthropic",
        "claude-haiku-5-5",
        "Best python http client?",
        "Use httpx; requests is fine for scripts.",
        ["https://example.com/review"],
    ),
]


def _report() -> Report:
    results = []
    for provider, model, prompt, text, urls in ANSWERS:
        extraction = extract_mentions(text, "httpx", ["requests", "aiohttp"])
        results.append(
            ProviderResult(
                provider=provider,
                model=model,
                prompt=prompt,
                response=text,
                mentions=extraction.mentions,
                citations=[Citation(source_name="web", url=u) for u in urls],
                latency_ms=1.0,
            )
        )
    results.append(
        ProviderResult(
            provider="anthropic",
            model="claude-haiku-5-5",
            prompt="Async http client for python?",
            response="",
            latency_ms=1.0,
            error="RateLimitError: slow down",
        )
    )
    return Report(
        brand="httpx",
        visibility_score=50.0,
        mention_count=4,
        provider_results=results,
        metrics=VisibilityMetrics(visibility_score=50.0, mention_count=4),
        measurement_tier="base_model",
    )


class TestAnswerRows:
    def test_one_row_per_answer_with_the_evidence(self):
        rows = answer_rows(_report())
        assert [r["answer"] for r in rows] == [0, 1, 2, 3]
        first = rows[0]
        assert first["provider"] == "openai" and first["model"] == "gpt-6-luna"
        assert first["prompt"] == "Best python http client?"
        assert first["brands_found"] == ["requests", "httpx"]
        assert first["target_mentioned"] is True
        assert first["target_position"] == 1
        assert first["target_rank"] == 2
        assert first["target_recommended"] is True
        assert first["cited_urls"] == ["https://www.python-httpx.org/"]
        assert "httpx" in first["excerpt"]
        assert first["ok"] is True and first["error"] is None

    def test_answer_without_the_target(self):
        row = answer_rows(_report())[1]
        assert row["brands_found"] == ["aiohttp"]
        assert row["target_mentioned"] is False
        assert row["target_position"] is None and row["target_rank"] is None
        assert row["excerpt"].startswith("aiohttp is the usual choice")

    def test_excerpt_is_bounded_and_on_one_line(self):
        rows = answer_rows(_report(), excerpt_chars=40)
        assert all(len(r["excerpt"]) <= 40 for r in rows)
        assert rows[1]["excerpt"].endswith("…")
        assert "\n" not in rows[0]["excerpt"]

    def test_failed_answer_is_kept_with_its_error(self):
        row = answer_rows(_report())[3]
        assert row["ok"] is False
        assert row["error"] == "RateLimitError: slow down"
        assert row["brands_found"] == [] and row["excerpt"] == ""

    @pytest.mark.parametrize(
        ("model", "expected"),
        [
            ("openai", [0, 1]),
            ("claude-haiku-5-5", [2, 3]),
            ("anthropic/claude-haiku-5-5", [2, 3]),
            ("OpenAI/GPT-6-LUNA", [0, 1]),
            ("mistral", []),
        ],
    )
    def test_filter_by_provider_or_model(self, model, expected):
        assert [r["answer"] for r in answer_rows(_report(), model=model)] == expected

    def test_filter_by_brand_named_or_not(self):
        report = _report()
        assert [r["answer"] for r in answer_rows(report, mentions="requests")] == [
            0,
            2,
        ]
        assert [r["answer"] for r in answer_rows(report, missing="httpx")] == [1]
        # Any name, tracked or not, matched as a whole name in the answer text.
        assert [r["answer"] for r in answer_rows(report, mentions="asyncio")] == [1]
        assert answer_rows(report, mentions="http") == []

    def test_missing_skips_failed_answers(self):
        # A failed request names nothing, but it is not evidence of absence.
        assert 3 not in [r["answer"] for r in answer_rows(_report(), missing="httpx")]

    def test_rejects_a_bad_excerpt_length(self):
        with pytest.raises(ValueError, match="excerpt_chars"):
            answer_rows(_report(), excerpt_chars=5)


@pytest.fixture
def saved(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "report.json"
    path.write_text(_report().model_dump_json(), encoding="utf-8")
    return path


class TestMcpAnswers:
    def test_pages_through_a_saved_report(self, saved):
        del saved
        page = mcp_server.answers("report.json", limit=2)
        assert page["brand"] == "httpx"
        assert page["measurement_tier"] == "base_model"
        assert page["total_answers"] == 4 and page["matched"] == 4
        assert [a["answer"] for a in page["answers"]] == [0, 1]
        assert page["next_offset"] == 2
        last = mcp_server.answers("report.json", offset=2, limit=2)
        assert [a["answer"] for a in last["answers"]] == [2, 3]
        assert last["next_offset"] is None
        json.dumps(page)

    def test_filters(self, saved):
        del saved
        page = mcp_server.answers("report.json", model="anthropic", mentions="httpx")
        assert [a["answer"] for a in page["answers"]] == [2]
        assert page["matched"] == 1

    def test_output_is_bounded(self, saved):
        del saved
        page = mcp_server.answers("report.json", excerpt_chars=60)
        assert all(len(a["excerpt"]) <= 60 for a in page["answers"])
        assert all("response" not in a for a in page["answers"])
        with pytest.raises(ValueError, match="limit"):
            mcp_server.answers("report.json", limit=101)

    def test_report_must_be_inside_the_working_directory(self, saved):
        with pytest.raises(ValueError, match="inside the working directory"):
            mcp_server.answers(str(saved.parent.parent / "x.json"))

    def test_is_registered_as_read_only_and_free(self):
        fn, read_only, open_world = mcp_server.TOOLS["answers"]
        assert fn is mcp_server.answers and read_only and not open_world
        assert "Free" in (fn.__doc__ or "")


class TestCliAnswers:
    def test_jsonl_has_one_answer_per_line(self, saved):
        result = CliRunner().invoke(
            app, ["answers", "--report", str(saved), "-f", "jsonl"]
        )
        assert result.exit_code == 0, result.output
        lines = result.stdout.strip().splitlines()
        assert len(lines) == 4
        rows = [json.loads(line) for line in lines]
        assert rows[0]["target_rank"] == 2
        # The CLI export carries the full answer text.
        assert rows[1]["response"].startswith("aiohttp is the usual choice")

    def test_filters_and_csv(self, saved):
        result = CliRunner().invoke(
            app,
            [
                "answers", "--report", str(saved), "--missing", "httpx",
                "-f", "csv",
            ],
        )  # fmt: skip
        assert result.exit_code == 0, result.output
        rows = list(csv.DictReader(io.StringIO(result.stdout)))
        assert [r["answer"] for r in rows] == ["1"]
        assert rows[0]["brands_found"] == "aiohttp"

    def test_json_and_limit(self, saved):
        result = CliRunner().invoke(
            app,
            ["answers", "--report", str(saved), "-m", "openai", "-f", "json"],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.stdout)
        assert [r["answer"] for r in data] == [0, 1]
        limited = CliRunner().invoke(
            app, ["answers", "--report", str(saved), "--limit", "1", "-f", "json"]
        )
        assert [r["answer"] for r in json.loads(limited.stdout)] == [0]

    def test_text_table(self, saved):
        result = CliRunner().invoke(app, ["answers", "--report", str(saved)])
        assert result.exit_code == 0, result.output
        assert "Best python http client?" in result.stdout
        assert "4 of 4 answers" in result.output

    def test_bad_report_is_a_clean_error(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{}", encoding="utf-8")
        result = CliRunner().invoke(app, ["answers", "--report", str(bad)])
        assert result.exit_code == 1
        assert "Error reading report" in result.output
