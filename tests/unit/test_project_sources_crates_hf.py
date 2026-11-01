"""crates.io and Hugging Face Hub sources (mocked HTTP only)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from promptbeacon.cli.main import app
from promptbeacon.projects import (
    HttpResponse,
    ProjectMetadataError,
    ProjectMetadataUnavailable,
    fetch_project,
    guess_category,
    parse_project_ref,
    profile_project,
    project_name_from_ref,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "projects"

REQWEST_README = (
    "<h1>reqwest</h1><p>An ergonomic, batteries-included HTTP Client for Rust.</p>"
    "<p>Inspired by <code>requests</code>. An alternative to hyper for most "
    "apps; compared to ureq it is async.</p>"
)
MINILM_README = (
    "---\npipeline_tag: sentence-similarity\nlicense: apache-2.0\n---\n\n"
    "# all-MiniLM-L6-v2\nThis is a [sentence-transformers](https://www.SBERT.net) "
    "model: It maps sentences & paragraphs to a 384 dimensional dense vector "
    "space.\n\nCompared to all-mpnet-base-v2 it is five times faster.\n"
)


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeHttp:
    """Answers from a {url-substring: response} table; 404 otherwise."""

    def __init__(self, routes: dict[str, HttpResponse | str]):
        self.routes = routes
        self.calls: list[str] = []

    def __call__(self, url: str, headers: dict[str, str]) -> HttpResponse:
        self.calls.append(url)
        assert headers["User-Agent"].startswith("promptbeacon/")
        for key, resp in self.routes.items():
            if key in url:
                return (
                    resp if isinstance(resp, HttpResponse) else HttpResponse(200, resp)
                )
        return HttpResponse(404, '{"errors": [{"detail": "Not Found"}]}')


def crates_http() -> FakeHttp:
    return FakeHttp(
        {
            "/readme": REQWEST_README,
            "crates.io/api/v1/crates/reqwest?include=": _fixture("crates_reqwest.json"),
        }
    )


def hf_model_http() -> FakeHttp:
    return FakeHttp(
        {
            "/raw/main/README.md": MINILM_README,
            "huggingface.co/api/models/sentence-transformers/all-MiniLM-L6-v2": _fixture(
                "hf_model_minilm.json"
            ),
        }
    )


# --- crates.io -------------------------------------------------------------------


def test_crates_source_reads_metadata_categories_and_readme():
    http = crates_http()
    meta = fetch_project("crates:reqwest", http=http, cache=False)
    assert meta.source == "crates" and meta.name == "reqwest"
    assert meta.language == "Rust"
    assert meta.description == "higher level HTTP client library"
    assert "http client" in [k.replace("-", " ") for k in meta.keywords]
    assert meta.url == "https://github.com/seanmonstar/reqwest"
    assert "batteries-included HTTP Client" in meta.readme
    assert "<p>" not in meta.readme
    # The version list is skipped; only the public crates.io API is called.
    assert all(u.startswith("https://crates.io/api/v1/crates/") for u in http.calls)
    assert "include=keywords,categories" in http.calls[0]


def test_crates_category_guess_and_peers():
    meta = fetch_project("crates:reqwest", http=crates_http(), cache=False)
    profile = profile_project(meta)
    assert profile.category.category == "rust http client"
    assert profile.category.basis == "description"
    assert "hyper" in profile.competitors and "ureq" in profile.competitors


def test_slash_pairs_in_descriptions_read_as_one_kind():
    from promptbeacon.projects import ProjectMetadata

    meta = ProjectMetadata(
        source="crates", ref="serde", name="serde", language="Rust",
        description="A generic serialization/deserialization framework",
    )  # fmt: skip
    assert guess_category(meta).category == "rust serialization framework"


def test_crates_readme_is_optional():
    http = FakeHttp(
        {"crates.io/api/v1/crates/reqwest?include=": _fixture("crates_reqwest.json")}
    )
    meta = fetch_project("crates:reqwest", http=http, cache=False)
    assert meta.readme == ""


@pytest.mark.parametrize(
    "ref", ["crates:reqwest", "crate:reqwest", "https://crates.io/crates/reqwest"]
)
def test_crates_reference_forms(ref):
    assert parse_project_ref(ref)[0] == "crates"
    assert fetch_project(ref, http=crates_http(), cache=False).name == "reqwest"


def test_crates_errors():
    with pytest.raises(ProjectMetadataError, match="not found"):
        fetch_project("crates:no-such-crate", http=FakeHttp({}), cache=False)
    with pytest.raises(ProjectMetadataError, match="valid crate"):
        fetch_project("crates:bad name", http=FakeHttp({}), cache=False)


# --- Hugging Face -----------------------------------------------------------------


def test_hf_model_uses_pipeline_tag_as_category():
    meta = fetch_project(
        "hf:sentence-transformers/all-MiniLM-L6-v2", http=hf_model_http(), cache=False
    )
    assert meta.source == "hf" and meta.name == "all-MiniLM-L6-v2"
    assert "sentence-transformers/all-MiniLM-L6-v2" in meta.aliases
    assert meta.description.startswith("This is a sentence-transformers model")
    assert "license:apache-2.0" not in meta.keywords
    guess = guess_category(meta)
    assert guess.category == "text embedding model"
    assert guess.confidence == "high"
    assert "pipeline_tag 'sentence-similarity'" in guess.basis
    assert profile_project(meta).competitors == ["all-mpnet-base-v2"]


def test_hf_dataset_uses_task_categories():
    http = FakeHttp(
        {
            "huggingface.co/api/datasets/rajpurkar/squad": _fixture(
                "hf_dataset_squad.json"
            )
        }
    )
    meta = fetch_project(
        "https://huggingface.co/datasets/rajpurkar/squad", http=http, cache=False
    )
    assert meta.ref == "datasets/rajpurkar/squad"
    assert meta.url == "https://huggingface.co/datasets/rajpurkar/squad"
    assert "SQuAD" in meta.aliases
    assert "reading comprehension dataset" in meta.description
    assert guess_category(meta).category == "question answering dataset"
    assert any("/datasets/rajpurkar/squad/raw/main/README.md" in u for u in http.calls)


def test_hf_space_without_hint_falls_back_to_description():
    space = {"id": "acme/demo", "sdk": "gradio", "tags": ["gradio"],
             "cardData": {"title": "Acme", "short_description": "A fast OCR app"}}  # fmt: skip
    http = FakeHttp({"api/spaces/acme/demo": json.dumps(space)})
    meta = fetch_project("hf:spaces/acme/demo", http=http, cache=False)
    assert meta.ref == "spaces/acme/demo" and meta.category_hint is None
    assert guess_category(meta).category == "ocr app"


def test_hf_errors():
    with pytest.raises(ProjectMetadataError, match="owner/name"):
        fetch_project("hf:just-a-name", http=FakeHttp({}), cache=False)
    private = HttpResponse(401, '{"error": "Repository not found"}')
    with pytest.raises(ProjectMetadataError, match="private or was not found"):
        fetch_project(
            "hf:acme/secret", http=FakeHttp({"huggingface.co": private}), cache=False
        )


def test_project_name_from_ref_needs_no_network():
    assert project_name_from_ref("crates:serde") == "serde"
    assert project_name_from_ref("hf:datasets/rajpurkar/squad") == "squad"
    assert project_name_from_ref("github:encode/httpx") == "httpx"


# --- CLI ----------------------------------------------------------------------------


def test_cli_scan_crate_demo():
    with patch("promptbeacon.projects.sources.default_http_get", new=crates_http()):
        result = CliRunner().invoke(
            app, ["scan", "--crate", "reqwest", "--demo", "-f", "json"]
        )
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["brand"] == "reqwest"
    assert data["categories"] == ["rust http client"]
    assert "crates: reqwest" in result.stderr


def test_cli_badge_for_hf_model(tmp_path):
    with patch("promptbeacon.projects.sources.default_http_get", new=hf_model_http()):
        result = CliRunner().invoke(
            app,
            ["card", "--hf", "sentence-transformers/all-MiniLM-L6-v2", "--demo",
             "-o", str(tmp_path / "card.svg")],
        )  # fmt: skip
    assert result.exit_code == 0, result.output
    svg = (tmp_path / "card.svg").read_text(encoding="utf-8")
    assert "Which text embedding model does AI recommend?" in svg


def test_cli_demo_carries_on_offline():
    def offline(url, _headers):
        raise ProjectMetadataUnavailable(f"Could not reach {url}: no network")

    with patch("promptbeacon.projects.sources.default_http_get", new=offline):
        result = CliRunner().invoke(
            app,
            ["scan", "--crate", "serde", "--demo", "-t", "rust serialization library",
             "-f", "json"],
        )  # fmt: skip
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["brand"] == "serde"
    assert "Demo continues offline" in result.stderr


def test_cli_real_scan_offline_is_an_error():
    def offline(url, _headers):
        raise ProjectMetadataUnavailable(f"Could not reach {url}: no network")

    with patch("promptbeacon.projects.sources.default_http_get", new=offline):
        result = CliRunner().invoke(app, ["scan", "--crate", "serde"])
    assert result.exit_code == 1
    assert "Could not reach" in result.output


def test_cli_only_one_project_source():
    result = CliRunner().invoke(app, ["scan", "--crate", "a", "--hf", "b/c", "--demo"])
    assert result.exit_code == 1
    assert "--crate" in result.output
