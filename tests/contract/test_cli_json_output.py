"""Contract tests for CLI JSON output."""
from __future__ import annotations

import json
import os
from pathlib import Path

from click.testing import CliRunner

from dev_stack.cli.main import cli


def test_init_json_contract() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Simulate a Python project so stack profile includes Python modules
        Path("setup.py").write_text("# placeholder")
        result = runner.invoke(cli, ["--json", "init"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["status"] == "success"
        assert payload["mode"] in {"greenfield", "reinit", "brownfield"}
        assert payload["manifest_path"].endswith("dev-stack.toml")
        assert "hooks" in payload["modules_installed"]
        assert "uv_project" in payload["modules_installed"]
        assert "sphinx_docs" in payload["modules_installed"]
        assert "conflicts" in payload
        manifest_path = Path(payload["manifest_path"])
        assert manifest_path.exists()
        assert (Path.cwd() / ".pre-commit-config.yaml").exists()


def test_status_json_contract() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Simulate a Python project so stack profile includes Python modules
        Path("setup.py").write_text("# placeholder")
        init_result = runner.invoke(cli, ["init"])
        assert init_result.exit_code == 0, init_result.output
        result = runner.invoke(cli, ["--json", "status"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["manifest_version"], payload
        assert payload["mode"] in {"greenfield", "brownfield", "reinit", "unknown"}
        assert payload["agent"]["cli"], payload
        assert isinstance(payload["modules"], dict)
        assert "hooks" in payload["modules"]
        assert "uv_project" in payload["modules"]
        assert "sphinx_docs" in payload["modules"]
        assert "last_pipeline_run" in payload


def _fake_agent_env() -> dict[str, str]:
    env = os.environ.copy()
    bin_dir = Path("fake-bin")
    bin_dir.mkdir(exist_ok=True)
    claude = bin_dir / "claude"
    claude.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    claude.chmod(0o755)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["DEV_STACK_AGENT"] = "claude"
    return env
