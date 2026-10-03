"""Project metadata sources and offline inference (mocked HTTP only)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from promptbeacon import Beacon
from promptbeacon.cli.main import app
from promptbeacon.projects import (
    HttpResponse,
    MetadataCache,
    MetadataSource,
    ProjectMetadata,
    ProjectMetadataError,
    available_sources,
    fetch_project,
    guess_category,
    guess_competitors,
    parse_project_ref,
    register_source,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "projects"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeHttp:
    """Records requests; answers from a {url-substring: response} table."""

    def __init__(self, routes: dict[str, HttpResponse | str]):
        self.routes = routes
        self.calls: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, headers: dict[str, str]) -> HttpResponse:
        self.calls.append((url, headers))
        for key, resp in self.routes.items():
            if key in url:
                return (
                    resp if isinstance(resp, HttpResponse) else HttpResponse(200, resp)
                )
        return HttpResponse(404, '{"message": "Not Found"}')


GITHUB_README = (
    "# FastAPI\n\nInspired by Flask. Compared to Django REST Framework it is "
    "faster. Unlike other tools... An alternative to the popular frameworks."
)


def github_http() -> FakeHttp:
    return FakeHttp(
        {
            "/readme": GITHUB_README,
            "api.github.com/repos/fastapi/fastapi": _fixture("github_fastapi.json"),
        }
    )


# --- sources --------------------------------------------------------------------


def test_github_source_parses_metadata_and_readme():
    meta = fetch_project("github:fastapi/fastapi", http=github_http(), cache=False)
    assert meta.name == "fastapi"
    assert meta.source == "github"
    assert "api" in meta.keywords
    assert meta.language == "Python"
    assert "Flask" in meta.readme


@pytest.mark.parametrize(
    "ref",
    [
        "fastapi/fastapi",
        "https://github.com/fastapi/fastapi",
        "github:fastapi/fastapi.git",
    ],
)
def test_github_reference_forms(ref):
    meta = fetch_project(ref, http=github_http(), cache=False)
    assert meta.ref == "fastapi/fastapi"


def test_pypi_source():
    http = FakeHttp({"pypi.org/pypi/httpx/json": _fixture("pypi_httpx.json")})
    meta = fetch_project("pypi:httpx", http=http, cache=False)
    assert meta.name == "httpx"
    assert meta.description == "The next generation HTTP client."
    assert meta.language == "Python"
    assert "WWW/HTTP" in meta.keywords


def test_npm_source_including_scoped_names():
    http = FakeHttp({"registry.npmjs.org/express/latest": _fixture("npm_express.json")})
    meta = fetch_project("npm:express", http=http, cache=False)
    assert meta.name == "express" and "framework" in meta.keywords

    scoped = json.dumps({"name": "@scope/widget", "description": "A UI toolkit"})
    http = FakeHttp({"registry.npmjs.org/@scope%2Fwidget/latest": scoped})
    meta = fetch_project("npm:@scope/widget", http=http, cache=False)
    assert meta.name == "widget" and meta.aliases == ["@scope/widget"]


def test_user_agent_is_always_sent():
    http = github_http()
    fetch_project("fastapi/fastapi", http=http, cache=False)
    assert all(h["User-Agent"].startswith("promptbeacon/") for _, h in http.calls)


def test_github_token_is_used_when_set(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_test")
    http = github_http()
    fetch_project("fastapi/fastapi", http=http, cache=False)
    assert http.calls[0][1]["Authorization"] == "Bearer ghs_test"


def test_github_token_absent_or_empty_sends_no_auth(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    http = github_http()
    fetch_project("fastapi/fastapi", http=http, cache=False)
    assert "Authorization" not in http.calls[0][1]


def test_not_found_is_a_clear_error():
    with pytest.raises(ProjectMetadataError, match="not found"):
        fetch_project("pypi:no-such-package-xyz", http=FakeHttp({}), cache=False)


def test_github_rate_limit_message_mentions_token():
    limited = HttpResponse(
        403, '{"message": "API rate limit exceeded"}',
        {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "9999999999"},
    )  # fmt: skip
    with pytest.raises(ProjectMetadataError, match="GITHUB_TOKEN"):
        fetch_project(
            "github:a/b", http=FakeHttp({"api.github.com": limited}), cache=False
        )


def test_invalid_references():
    with pytest.raises(ProjectMetadataError):
        parse_project_ref("not a ref")
    with pytest.raises(ProjectMetadataError):
        fetch_project("pypi:bad name!", http=FakeHttp({}), cache=False)
    with pytest.raises(ProjectMetadataError, match="Available"):
        fetch_project("x", kind="nope", http=FakeHttp({}), cache=False)


def test_malformed_response_is_a_clear_error():
    http = FakeHttp({"pypi.org": "not json"})
    with pytest.raises(ProjectMetadataError, match="Unexpected"):
        fetch_project("pypi:httpx", http=http, cache=False)


def test_cache_avoids_repeat_requests(tmp_path):
    cache = MetadataCache(tmp_path)
    http = FakeHttp({"pypi.org/pypi/httpx/json": _fixture("pypi_httpx.json")})
    fetch_project("pypi:httpx", http=http, cache=cache)
    fetch_project("pypi:httpx", http=http, cache=cache)
    assert len(http.calls) == 1


def test_new_sources_are_one_small_class():
    class CratesSource(MetadataSource):
        kind = "crates"
        label = "crates.io"
        example = "serde"

        def fetch(self, ref: str) -> ProjectMetadata:
            data = self._get(f"https://crates.io/api/v1/crates/{ref}").json()["crate"]
            return ProjectMetadata(
                source=self.kind, ref=ref, name=data["name"],
                description=data["description"], keywords=data["keywords"],
                language="Rust",
            )  # fmt: skip

    register_source(CratesSource)
    try:
        crate = {"crate": {"name": "serde", "description": "A serialization framework",
                           "keywords": ["serde", "serialization"]}}  # fmt: skip
        meta = fetch_project(
            "crates:serde", http=FakeHttp({"crates.io": json.dumps(crate)}), cache=False
        )
        assert "crates" in available_sources()
        assert guess_category(meta).category == "rust serialization framework"
    finally:
        from promptbeacon.projects import sources

        sources._SOURCES.pop("crates", None)


# --- inference -------------------------------------------------------------------


def _meta(**kw) -> ProjectMetadata:
    base = {"source": "github", "ref": "o/proj", "name": "proj"}
    return ProjectMetadata(**{**base, **kw})


def test_category_from_real_metadata_fixtures():
    httpx = fetch_project(
        "pypi:httpx",
        http=FakeHttp({"pypi.org": _fixture("pypi_httpx.json")}),
        cache=False,
    )
    express = fetch_project(
        "npm:express",
        http=FakeHttp({"npmjs": _fixture("npm_express.json")}),
        cache=False,
    )
    fastapi = fetch_project("fastapi/fastapi", http=github_http(), cache=False)
    assert guess_category(httpx).category == "python http client"
    assert guess_category(express).category == "javascript web framework"
    assert guess_category(fastapi).category == "python api framework"


def test_category_ignores_brand_and_marketing_words():
    meta = _meta(name="Zippy", description="Zippy: a blazing fast, modern JSON parser.")
    assert guess_category(meta).category == "json parser"


def test_non_latin_description_falls_back_to_topics():
    meta = _meta(
        description="一个快速的网络框架", keywords=["web", "framework"], language="Go"
    )
    guess = guess_category(meta)
    assert guess.category == "go web framework"


def test_no_metadata_gives_no_category():
    guess = guess_category(_meta())
    assert guess.category is None and guess.confidence == "low"


def test_competitors_from_readme_and_stop_words():
    meta = _meta(readme=GITHUB_README, name="fastapi")
    assert guess_competitors(meta) == ["Flask", "Django"]
    assert guess_competitors(_meta(readme="An alternative to the other tools.")) == []
    assert guess_competitors(_meta(readme="")) == []


# --- Beacon / CLI ------------------------------------------------------------------


def test_beacon_from_project_demo_scan():
    beacon = Beacon.from_project("fastapi/fastapi", http=github_http(), cache=False)
    assert beacon.brand == "fastapi"
    assert beacon.project is not None
    report = beacon.demo().scan()
    assert report.categories == ["python api framework"]
    assert set(report.competitor_comparison) == {"Flask", "Django"}
    assert all("python api framework" in r.prompt for r in report.provider_results)


def test_beacon_from_project_infer_falls_back_to_guess_in_demo():
    beacon = Beacon.from_project(
        "fastapi/fastapi", infer=True, http=github_http(), cache=False
    )
    report = beacon.demo().scan()
    assert report.categories == ["python api framework"]


def test_cli_scan_pypi_demo():
    http = FakeHttp({"pypi.org/pypi/httpx/json": _fixture("pypi_httpx.json")})
    with patch("promptbeacon.projects.sources.default_http_get", new=http):
        result = CliRunner().invoke(
            app, ["scan", "--pypi", "httpx", "--demo", "-f", "json"]
        )
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["brand"] == "httpx"
    assert data["categories"] == ["python http client"]
    assert "python http client" in result.stderr


def test_cli_category_overrides_guess():
    http = FakeHttp({"pypi.org/pypi/httpx/json": _fixture("pypi_httpx.json")})
    with patch("promptbeacon.projects.sources.default_http_get", new=http):
        result = CliRunner().invoke(
            app, ["scan", "--pypi", "httpx", "-t", "async http library", "--demo",
                  "-f", "json"],
        )  # fmt: skip
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["categories"] == ["async http library"]


def test_cli_project_error_is_clean():
    with patch("promptbeacon.projects.sources.default_http_get", new=FakeHttp({})):
        result = CliRunner().invoke(app, ["scan", "--npm", "no-such-pkg", "--demo"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_cli_only_one_project_option():
    result = CliRunner().invoke(app, ["scan", "--pypi", "a", "--npm", "b", "--demo"])
    assert result.exit_code == 1


def test_cli_card_for_repo(tmp_path):
    with patch("promptbeacon.projects.sources.default_http_get", new=github_http()):
        result = CliRunner().invoke(
            app, ["card", "--repo", "fastapi/fastapi", "--demo", "-o",
                  str(tmp_path / "c.svg")],
        )  # fmt: skip
    assert result.exit_code == 0, result.output
    assert "Which python api framework does AI recommend?" in (
        tmp_path / "c.svg"
    ).read_text(encoding="utf-8")
