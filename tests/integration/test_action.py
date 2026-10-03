"""Run the composite GitHub Action's shell steps locally (demo mode).

A small interpreter for the subset of expressions action.yml uses, so the
Action's argument handling, outputs, summary and gate are tested for real.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[2]
ACTION = yaml.safe_load((ROOT / "action.yml").read_text(encoding="utf-8"))

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("bash") is None or os.name == "nt", reason="bash"),
]


def _parse_outputs(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                out[key] = value
    return out


def run_action(tmp_path: Path, inputs: dict[str, str]) -> dict:
    """Execute every step except install; returns outputs, summary, exit code."""
    values = {k: str(v.get("default", "")) for k, v in ACTION["inputs"].items()}
    values.update(inputs)
    temp = tmp_path / "runner"
    temp.mkdir()
    step_outputs: dict[str, dict[str, str]] = {}
    summary = tmp_path / "summary.md"
    bindir = Path(sys.executable).parent

    def expr(text: str) -> str:
        def sub(m: re.Match) -> str:
            e = m.group(1).strip()
            if e.startswith("inputs."):
                return values[e[len("inputs.") :]]
            if e.startswith("steps."):
                _, sid, _, key = e.split(".", 3)
                return step_outputs.get(sid, {}).get(key, "")
            if e == "runner.temp":
                return str(temp)
            if e == "github.event_name":
                return "push"
            return ""

        return re.sub(r"\$\{\{(.*?)\}\}", sub, str(text))

    last_code = 0
    for step in ACTION["runs"]["steps"]:
        if step["name"].startswith("Install") or step["name"].startswith("Update PR"):
            continue
        cond = step.get("if")
        if cond and not any(
            values[k] for k in re.findall(r"inputs\.([\w-]+) != ''", cond)
        ):
            continue
        out_file = tmp_path / f"out-{step.get('id', 'x')}"
        env = {
            **os.environ,
            "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}",
            "RUNNER_TEMP": str(temp),
            "GITHUB_OUTPUT": str(out_file),
            "GITHUB_STEP_SUMMARY": str(summary),
        }
        env.update({k: expr(v) for k, v in step.get("env", {}).items()})
        proc = subprocess.run(
            ["bash", "-e", "-c", expr(step["run"])],
            env=env,
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )
        last_code = proc.returncode
        if "id" in step:
            step_outputs[step["id"]] = _parse_outputs(out_file)
        if proc.returncode != 0:
            break
    return {
        "outputs": {name: expr(o["value"]) for name, o in ACTION["outputs"].items()},
        "summary": summary.read_text(encoding="utf-8") if summary.exists() else "",
        "exit": last_code,
        "temp": temp,
    }


def test_action_demo_passes_with_outputs_and_summary(tmp_path):
    result = run_action(
        tmp_path,
        {
            "brand": "Nike",
            "category": "running shoes",
            "competitors": "Adidas\nNew Balance",
            "demo": "true",
            "badge-path": ".promptbeacon/badge.svg",
            "badge-endpoint-path": ".promptbeacon/badge.json",
            "card-path": ".promptbeacon/card.svg",
        },
    )
    assert result["exit"] == 0
    out = result["outputs"]
    assert float(out["score"]) >= 0
    assert 0 <= float(out["share-of-voice"]) <= 1
    assert out["tier"] == "demo"
    assert out["passed"] == "true"
    report = json.loads(Path(out["report-path"]).read_text(encoding="utf-8"))
    assert report["categories"] == ["running shoes"]  # spaces preserved
    assert set(report["competitor_comparison"]) == {"Adidas", "New Balance"}
    assert "### AI visibility: Nike · running shoes" in result["summary"]
    assert (tmp_path / ".promptbeacon/badge.svg").exists()
    assert (
        json.loads((tmp_path / ".promptbeacon/badge.json").read_text())["schemaVersion"]
        == 1
    )
    assert (tmp_path / ".promptbeacon/card.svg").exists()
    comment = (result["temp"] / "promptbeacon-comment.md").read_text()
    assert comment.startswith("<!-- promptbeacon-report -->")


def test_action_gate_fails_after_reporting(tmp_path):
    result = run_action(
        tmp_path,
        {"brand": "Nike", "category": "running shoes", "demo": "true",
         "min-score": "101"},
    )  # fmt: skip
    assert result["exit"] != 0
    assert result["outputs"]["passed"] == "false"
    assert "**Failed**" in result["summary"]


def test_action_legacy_space_separated_lists(tmp_path):
    result = run_action(
        tmp_path,
        {"brand": "Nike", "categories": "shoes apparel", "competitors": "Adidas Puma",
         "demo": "true"},
    )  # fmt: skip
    assert result["exit"] == 0
    report = json.loads(
        Path(result["outputs"]["report-path"]).read_text(encoding="utf-8")
    )
    assert report["categories"] == ["shoes", "apparel"]
    assert set(report["competitor_comparison"]) == {"Adidas", "Puma"}
