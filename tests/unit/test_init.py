"""`promptbeacon init`: detection, plan, preview, safe writes, idempotency."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from promptbeacon.cli.main import app
from promptbeacon.init_project import (
    GENERATED_MARKER,
    build_plan,
    detect_project,
    github_ref_from_url,
    read_git,
    round_up_cap,
)
from promptbeacon.protocol import load_protocol

WORKFLOW = ".github/workflows/ai-visibility.yml"


def make_python_project(root: Path, *, remote: str | None = None) -> Path:
    (root / "pyproject.toml").write_text(
        '[project]\nname = "fetchy"\nversion = "0.1.0"\n'
        'description = "A tiny async HTTP client for Python."\n'
        'keywords = ["http", "client"]\n',
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        "# fetchy\n\nA small alternative to requests, inspired by httpx.\n",
        encoding="utf-8",
    )
    if remote:
        git = root / ".git"
        (git / "refs" / "remotes" / "origin").mkdir(parents=True)
        (git / "config").write_text(
            f'[core]\n\tbare = false\n[remote "origin"]\n\turl = {remote}\n',
            encoding="utf-8",
        )
        (git / "HEAD").write_text("ref: refs/heads/feature\n", encoding="utf-8")
        (git / "refs" / "remotes" / "origin" / "HEAD").write_text(
            "ref: refs/remotes/origin/main\n", encoding="utf-8"
        )
    return root


def run(root: Path, *args: str, **kwargs):
    return CliRunner().invoke(app, ["init", str(root), *args], **kwargs)


# --- detection -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "ref"),
    [
        ("https://github.com/encode/httpx.git", "encode/httpx"),
        ("git@github.com:encode/httpx.git", "encode/httpx"),
        ("https://github.com/encode/httpx", "encode/httpx"),
        ("git+https://github.com/expressjs/express.git", "expressjs/express"),
        ("https://gitlab.com/a/b.git", None),
        (None, None),
    ],
)
def test_github_ref_from_url(url, ref):
    assert github_ref_from_url(url) == ref


def test_detects_pyproject_readme_and_git_remote(tmp_path):
    root = make_python_project(tmp_path, remote="git@github.com:example/fetchy.git")
    project = detect_project(root)
    assert project.name == "fetchy" and project.language == "Python"
    assert project.github == "example/fetchy"
    assert project.branch == "main"  # the remote's default branch, not HEAD
    assert project.found == ["pyproject.toml", "git remote"]
    assert read_git(tmp_path / "nowhere") == (None, None)


def test_detects_package_json_and_cargo(tmp_path):
    js = tmp_path / "js"
    js.mkdir()
    (js / "package.json").write_text(
        json.dumps(
            {
                "name": "@acme/router",
                "description": "A fast router for Node.js web apps",
                "keywords": ["router", "http"],
                "repository": {"url": "git+https://github.com/acme/router.git"},
                "devDependencies": {"typescript": "^5"},
            }
        ),
        encoding="utf-8",
    )
    project = detect_project(js)
    assert project.name == "router" and project.language == "TypeScript"
    assert project.github == "acme/router"

    rs = tmp_path / "rs"
    rs.mkdir()
    (rs / "Cargo.toml").write_text(
        '[package]\nname = "tinyhttp"\ndescription = "A minimal HTTP client"\n'
        'keywords = ["http"]\ncategories = ["web-programming::http-client"]\n'
        'repository = "https://github.com/acme/tinyhttp"\n',
        encoding="utf-8",
    )
    project = detect_project(rs)
    assert project.name == "tinyhttp" and project.language == "Rust"
    assert project.github == "acme/tinyhttp"
    assert build_plan(project).category == "rust http client"


def test_plan_proposes_category_with_basis(tmp_path):
    plan = build_plan(detect_project(make_python_project(tmp_path)))
    assert plan.brand == "fetchy"
    assert plan.category == "python async http client"
    assert plan.category_basis == "pyproject.toml description"
    assert plan.competitors == ["requests", "httpx"]
    assert plan.secrets == ["OPENAI_API_KEY"]
    assert plan.max_cost == 0.05 and plan.estimate_usd and plan.estimate_usd > 0


def test_round_up_cap():
    assert round_up_cap(0) == 0.05
    assert round_up_cap(0.0025) == 0.05
    assert round_up_cap(0.03) == 0.1
    assert round_up_cap(1.0) == 2.0


# --- workflow content ------------------------------------------------------------


def test_workflow_uses_the_action_with_commented_models(tmp_path):
    root = make_python_project(tmp_path, remote="https://github.com/example/fetchy")
    plan = build_plan(detect_project(root), competitors=["requests", "aiohttp"])
    content = plan.files[0].content
    assert content.startswith(GENERATED_MARKER)
    assert "# models: |" in content and "#   openai=gpt-6-luna" in content
    workflow = yaml.safe_load(content)
    step = workflow["jobs"]["scan"]["steps"][1]
    assert step["uses"] == "yotambraun/promptbeacon@v1"
    inputs = step["with"]
    assert inputs["brand"] == "fetchy"
    assert inputs["category"] == "python async http client"
    assert inputs["competitors"].split() == ["requests", "aiohttp"]
    assert inputs["max-cost"] == "0.05"
    assert inputs["trend-path"] == ".promptbeacon/trend.json"
    assert inputs["rank-badge-path"] == ".promptbeacon/rank.svg"
    assert step["env"] == {"OPENAI_API_KEY": "${{ secrets.OPENAI_API_KEY }}"}
    assert "providers" not in inputs
    # Every input the workflow sets is one the Action declares.
    action = yaml.safe_load(Path("action.yml").read_text(encoding="utf-8"))
    assert set(inputs) <= set(action["inputs"])


def test_models_and_providers_flags_reach_the_workflow(tmp_path):
    root = make_python_project(tmp_path)
    plan = build_plan(
        detect_project(root),
        category="python http client",
        providers=["openai", "google"],
        models=["anthropic=claude-sonnet-5-5"],
    )
    inputs = yaml.safe_load(plan.files[0].content)["jobs"]["scan"]["steps"][1]["with"]
    assert inputs["providers"] == "openai google"
    assert inputs["models"].strip() == "anthropic=claude-sonnet-5-5"
    assert plan.secrets == ["OPENAI_API_KEY", "GOOGLE_API_KEY"]


def test_badge_snippets_use_shields_with_the_default_branch(tmp_path):
    root = make_python_project(tmp_path, remote="https://github.com/example/fetchy")
    plan = build_plan(detect_project(root), competitors=["a", "b"])
    assert "raw.githubusercontent.com%2Fexample%2Ffetchy%2Fmain%2F.promptbeacon" in (
        plan.badge_markdown
    )
    assert plan.rank_badge_markdown and "rank.json" in plan.rank_badge_markdown
    other = tmp_path / "no-remote"
    other.mkdir()
    no_remote = build_plan(detect_project(make_python_project(other)))
    assert no_remote.badge_markdown.startswith(
        "[![AI visibility](.promptbeacon/badge.svg)"
    )


# --- CLI ------------------------------------------------------------------------


def test_dry_run_writes_nothing_and_shows_the_workflow(tmp_path):
    root = make_python_project(tmp_path)
    result = run(root, "--dry-run")
    assert result.exit_code == 0, result.output
    assert "create .github/workflows/ai-visibility.yml" in result.stdout
    assert "uses: yotambraun/promptbeacon@v1" in result.stdout
    assert "Dry run: nothing was written." in result.stdout
    assert "gh secret set OPENAI_API_KEY" in result.stdout
    assert "Next steps" in result.stdout
    assert not (root / ".github").exists()


def test_non_terminal_without_yes_writes_nothing(tmp_path):
    root = make_python_project(tmp_path)
    result = run(root)
    assert result.exit_code == 0, result.output
    assert "Re-run with --yes" in " ".join(result.stdout.split())
    assert not (root / WORKFLOW).exists()


def test_yes_writes_then_rerun_is_idempotent(tmp_path):
    root = make_python_project(tmp_path)
    first = run(root, "--yes", "-c", "requests", "-c", "aiohttp")
    assert first.exit_code == 0, first.output
    content = (root / WORKFLOW).read_text(encoding="utf-8")
    second = run(root, "--yes", "-c", "requests", "-c", "aiohttp")
    assert second.exit_code == 0, second.output
    assert "is up to date" in second.stdout
    assert "Nothing to write" in second.stdout
    assert (root / WORKFLOW).read_text(encoding="utf-8") == content


def test_changed_file_needs_force_or_confirmation(tmp_path):
    root = make_python_project(tmp_path)
    (root / ".github/workflows").mkdir(parents=True)
    (root / WORKFLOW).write_text("name: mine\n", encoding="utf-8")
    result = run(root, "--yes")
    assert result.exit_code == 0, result.output
    assert "(not written by init)" in result.stdout
    assert "-name: mine" in result.stdout  # the diff is shown
    assert "--force" in result.stdout
    assert (root / WORKFLOW).read_text(encoding="utf-8") == "name: mine\n"

    forced = run(root, "--yes", "--force")
    assert forced.exit_code == 0, forced.output
    assert (root / WORKFLOW).read_text(encoding="utf-8").startswith(GENERATED_MARKER)


def test_interactive_flow_asks_and_respects_answers(tmp_path, monkeypatch):
    monkeypatch.setattr("promptbeacon.cli.main._is_interactive", lambda: True)
    root = make_python_project(tmp_path)
    (root / ".github/workflows").mkdir(parents=True)
    (root / WORKFLOW).write_text("name: mine\n", encoding="utf-8")
    # category, competitors, replace? (no), demo? (no)
    answers = "python http client\nrequests, aiohttp\nn\nn\n"
    result = run(root, input=answers)
    assert result.exit_code == 0, result.output
    assert (root / WORKFLOW).read_text(encoding="utf-8") == "name: mine\n"
    assert "Nothing was written." in result.stdout

    (root / WORKFLOW).unlink()
    answers = "python http client\nrequests, aiohttp\ny\nn\n"  # write? yes
    result = run(root, input=answers)
    assert result.exit_code == 0, result.output
    inputs = yaml.safe_load((root / WORKFLOW).read_text(encoding="utf-8"))["jobs"][
        "scan"
    ]["steps"][1]["with"]
    assert inputs["category"] == "python http client"
    assert inputs["competitors"].split() == ["requests", "aiohttp"]


def test_demo_scan_is_labelled(tmp_path):
    root = make_python_project(tmp_path)
    result = run(root, "--dry-run", "--demo")
    assert result.exit_code == 0, result.output
    assert "DEMO — canned answers, not a measurement." in result.stdout
    assert "Mentions per project (demo data)" in result.stdout


def test_protocol_is_written_pinned_and_reused(tmp_path):
    root = make_python_project(tmp_path)
    result = run(root, "--yes", "--protocol", "-c", "requests", "-c", "aiohttp")
    assert result.exit_code == 0, result.output
    proto = load_protocol(root / ".promptbeacon/protocol.json")
    assert proto.brand == "fetchy" and proto.models == {"openai": "gpt-6-luna"}
    assert len(proto.prompts) == 10 and all("{category}" in p for p in proto.prompts)
    inputs = yaml.safe_load((root / WORKFLOW).read_text(encoding="utf-8"))["jobs"][
        "scan"
    ]["steps"][1]["with"]
    assert inputs["protocol"] == ".promptbeacon/protocol.json"
    again = run(root, "--yes")
    assert again.exit_code == 0, again.output
    assert ".promptbeacon/protocol.json is up to date" in again.stdout
    assert "Nothing to write" in again.stdout


def test_protocol_scan_keeps_the_category(tmp_path):
    root = make_python_project(tmp_path)
    run(root, "--yes", "--protocol", "-c", "requests", "-c", "aiohttp")
    result = CliRunner().invoke(
        app,
        ["scan", "--protocol", str(root / ".promptbeacon/protocol.json"), "--demo",
         "-f", "json"],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["categories"] == ["python async http client"]


def test_json_plan(tmp_path):
    root = make_python_project(tmp_path)
    result = run(root, "-f", "json")
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["brand"] == "fetchy"
    assert data["files"][0]["status"] == "create"
    assert data["written"] == []
    assert data["next_steps"]


def test_no_project_and_no_category_are_clear_errors(tmp_path):
    empty = run(tmp_path, "--dry-run")
    assert empty.exit_code == 1
    assert "--brand" in empty.output
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "zz"\n', "utf-8")
    nocat = run(tmp_path, "--dry-run")
    assert nocat.exit_code == 1
    assert "--category" in nocat.output


def test_works_without_api_keys(tmp_path):
    root = make_python_project(tmp_path)
    result = run(root, "--dry-run")
    assert "No provider key is set locally either" in " ".join(result.stdout.split())


@pytest.mark.parametrize(
    "template", sorted(Path("examples/workflows").glob("*.yml")), ids=lambda p: p.name
)
def test_workflow_templates_only_use_declared_action_inputs(template):
    action = yaml.safe_load(Path("action.yml").read_text(encoding="utf-8"))
    workflow = yaml.safe_load(template.read_text(encoding="utf-8"))
    for job in workflow["jobs"].values():
        for step in job["steps"]:
            if step.get("uses", "").startswith("yotambraun/promptbeacon"):
                assert set(step.get("with", {})) <= set(action["inputs"])
