"""Integration tests covering brownfield initialization."""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from dev_stack.cli.main import cli


def test_brownfield_init_prompts_and_respects_skip() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        repo_file = Path(".pre-commit-config.yaml")
        repo_file.write_text("user config\n", encoding="utf-8")

        result = runner.invoke(cli, ["init"], input="s\n")
        assert result.exit_code == 0, result.output
        assert "CONFLICT" in result.output
        assert repo_file.read_text(encoding="utf-8") == "user config\n"
        assert (Path("dev-stack.toml")).exists()


def test_brownfield_init_dry_run_reports_conflicts() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path(".pre-commit-config.yaml").write_text("user config\n", encoding="utf-8")

        result = runner.invoke(cli, ["--dry-run", "init"])
        assert result.exit_code == 0, result.output
        assert "Dry run summary" in result.output
        assert not Path("dev-stack.toml").exists()