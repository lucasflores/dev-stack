"""Contract tests for ``dev-stack release`` CLI — JSON schema compliance."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from dev_stack.cli.main import cli
from dev_stack.vcs.commit_parser import CommitSummary
from dev_stack.vcs.release import ReleaseContext


def _dummy_context(*, hard_failures=None) -> ReleaseContext:
    return ReleaseContext(
        current_version="1.2.0",
        next_version="1.3.0",
        bump_type="minor",
        commits=[
            CommitSummary(
                sha="a" * 40,
                short_sha="a" * 7,
                subject="feat(cli): add release",
                type="feat",
                scope="cli",
                description="add release",
            ),
        ],
        has_breaking=False,
        hard_failures=hard_failures or [],
        tag_name="v1.3.0",
    )


class TestReleaseDryRunJson:
    def test_schema_compliance(self, monkeypatch, tmp_path: Path) -> None:
        monkeypatch.chdir(tmp_path)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "1.2.0"\n')

        with patch(
            "dev_stack.vcs.release.prepare_release",
            return_value=_dummy_context(),
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["release", "--dry-run", "--json"])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["status"] == "dry_run"
        assert data["current_version"] == "1.2.0"
        assert data["next_version"] == "1.3.0"
        assert data["bump_type"] == "minor"
        assert isinstance(data["commits_analyzed"], int)
        assert isinstance(data["breaking_changes"], int)
        assert data["tag_created"] is None
        assert data["pyproject_updated"] is False
        assert data["changelog_updated"] is False
        assert data["hard_failures"] == []


class TestReleaseBlockedJson:
    def test_exit_code_6(self, monkeypatch, tmp_path: Path) -> None:
        from dev_stack.vcs.release import HardFailure

        monkeypatch.chdir(tmp_path)

        ctx = _dummy_context(hard_failures=[
            HardFailure(sha="abc1234", subject="feat(cli): add pr", failed_stages=["typecheck"]),
        ])
        with patch(
            "dev_stack.vcs.release.prepare_release",
            return_value=ctx,
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["release", "--json"])

        assert result.exit_code == 6
        data = json.loads(result.output)
        assert data["status"] == "blocked"
        assert len(data["hard_failures"]) == 1
        assert data["hard_failures"][0]["failed_stages"] == ["typecheck"]
