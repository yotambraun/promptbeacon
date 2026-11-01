"""LiteLLM loads only for live requests, with the bundled price map by default."""

from __future__ import annotations

import os
import subprocess
import sys

from promptbeacon.providers import litellm_client


def _run(code: str, **env: str) -> str:
    environ = {
        k: v for k, v in os.environ.items() if k != "LITELLM_LOCAL_MODEL_COST_MAP"
    }
    environ.update(env)
    proc = subprocess.run(
        [sys.executable, "-W", "error", "-c", code],
        capture_output=True,
        text=True,
        timeout=120,
        env=environ,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    return proc.stdout.strip()


def test_import_and_demo_do_not_load_litellm():
    out = _run(
        "import sys\n"
        "from promptbeacon import Beacon\n"
        "Beacon('Nike').demo().with_category('running shoes').scan()\n"
        "print('litellm' in sys.modules)"
    )
    assert out == "False"


def test_live_path_loads_litellm_with_the_bundled_price_map():
    out = _run(
        "import os, sys\n"
        "from promptbeacon.providers.litellm_client import load_litellm\n"
        "load_litellm()\n"
        "print('litellm' in sys.modules, os.environ['LITELLM_LOCAL_MODEL_COST_MAP'])"
    )
    assert out == "True True"


def test_user_choice_of_price_map_is_respected(monkeypatch):
    monkeypatch.setattr(litellm_client, "_litellm_module", None)
    monkeypatch.setenv("LITELLM_LOCAL_MODEL_COST_MAP", "False")
    litellm_client.load_litellm()
    assert os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] == "False"
