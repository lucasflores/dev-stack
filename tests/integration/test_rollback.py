"""Integration tests for rollback command."""
from __future__ import annotations

import subprocess
from pathlib import Path

from click.testing import CliRunner

from dev_stack.cli.main import cli


def _run_git(args: list[str]) -> None:
    subprocess.run(["git", *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _prepare_repo() -> None:
    _run_git(["init"])
    _run_git(["config", "user.email", "dev-stack@example.com"])
    _run_git(["config", "user.name", "Dev Stack"])
    Path("README.md").write_text("seed\n", encoding="utf-8")
    _run_git(["add", "README.md"])
    _run_git(["commit", "-m", "seed"])


def test_rollback_restores_pre_init_state() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _prepare_repo()
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0, result.output
        assert Path("dev-stack.toml").exists()
        assert Path(".pre-commit-config.yaml").exists()

        rollback = runner.invoke(cli, ["rollback"])
        assert rollback.exit_code == 0, rollback.output
        # Files introduced by init should be removed after rollback
        assert not Path("dev-stack.toml").exists()
        assert not Path(".pre-commit-config.yaml").exists()