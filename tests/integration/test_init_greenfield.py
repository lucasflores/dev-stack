"""Integration tests for dev-stack init."""
from __future__ import annotations

import stat
import tomllib
from pathlib import Path

from click.testing import CliRunner

from dev_stack.cli.main import cli


def test_greenfield_init_creates_expected_files() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0, result.output

        manifest_path = Path("dev-stack.toml")
        assert manifest_path.exists()
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["stack"]["version"] == "0.1.0"
        assert manifest["modules"]["hooks"]["installed"] is True

        hook_script = Path("scripts/hooks/pre-commit")
        git_hook = Path(".git/hooks/pre-commit")
        config_file = Path(".pre-commit-config.yaml")
        assert hook_script.exists()
        assert git_hook.exists()
        assert config_file.exists()
        assert hook_script.stat().st_mode & stat.S_IXUSR
        assert git_hook.stat().st_mode & stat.S_IXUSR

        # Idempotency: running again with --force should not change manifest content
        before = manifest_path.read_text(encoding="utf-8")
        result_second = runner.invoke(cli, ["init", "--force"])
        assert result_second.exit_code == 0, result_second.output
        after = manifest_path.read_text(encoding="utf-8")
        assert before == after