"""Contract tests for ``dev-stack changelog`` JSON output — tests/contract/test_cli_changelog.py

Validates that JSON output matches the schema in cli-contract.md.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from dev_stack.cli.main import cli


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


class TestChangelogJsonSchema:
    """Verify --json output matches contract."""

    def test_error_when_git_cliff_missing(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        with patch("dev_stack.vcs.changelog.shutil.which", return_value=None):
            result = runner.invoke(cli, ["changelog", "--json"], catch_exceptions=False)

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["status"] == "error"
        assert "error" in data
        assert "help" in data

    def test_success_json_schema(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        (tmp_path / "cliff.toml").write_text("[changelog]\n")
        monkeypatch.chdir(tmp_path)

        with patch("dev_stack.vcs.changelog.shutil.which", return_value="/usr/bin/git-cliff"):
            with patch("dev_stack.vcs.changelog.subprocess.run") as mock_run:
                ver_mock = MagicMock(stdout="git-cliff 2.4.0", returncode=0)
                gen_mock = MagicMock(
                    stdout="## [Unreleased]\n\n- feat: something 🤖\n",
                    returncode=0,
                )
                mock_run.side_effect = [ver_mock, gen_mock]

                result = runner.invoke(
                    cli, ["changelog", "--json"], catch_exceptions=False
                )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "success"
        assert "output_file" in data
        assert "mode" in data
        assert isinstance(data["versions_rendered"], int)
        assert isinstance(data["total_commits_processed"], int)
        assert isinstance(data["ai_commits_annotated"], int)
        assert isinstance(data["human_edited_annotated"], int)
        assert "git_cliff_version" in data
