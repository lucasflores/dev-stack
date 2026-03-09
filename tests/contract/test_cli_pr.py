"""Contract tests for ``dev-stack pr`` JSON output — tests/contract/test_cli_pr.py

Validates that JSON output matches the schema in cli-contract.md.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from dev_stack.cli.main import cli


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def repo_with_commits(tmp_path: Path) -> Path:
    """Create a git repo with a few conventional commits on a feature branch."""
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"],
        capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Test"],
        capture_output=True, check=True,
    )
    # Create initial commit on main
    (tmp_path / "README.md").write_text("# test\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "init"],
        capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "branch", "-M", "main"],
        capture_output=True, check=True,
    )

    # Create feature branch with commits
    subprocess.run(
        ["git", "-C", str(tmp_path), "checkout", "-b", "feat/test-pr"],
        capture_output=True, check=True,
    )

    (tmp_path / "src.py").write_text("x = 1\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m",
         "feat(cli): add pr command\n\nAgent: claude\nSpec-Ref: specs/004/spec.md\nPipeline: lint=pass,test=pass"],
        capture_output=True, check=True,
    )

    (tmp_path / "test.py").write_text("assert True\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "test: add unit tests"],
        capture_output=True, check=True,
    )

    return tmp_path


class TestPRJsonSchema:
    """Verify --json output matches cli-contract.md schema."""

    def test_dry_run_json_schema(
        self, runner: CliRunner, repo_with_commits: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(repo_with_commits)
        result = runner.invoke(cli, ["pr", "--dry-run", "--json"], catch_exceptions=False)
        assert result.exit_code == 0

        data = json.loads(result.output)
        # Required fields per contract
        assert data["status"] == "dry_run"
        assert "branch" in data
        assert "base" in data
        assert isinstance(data["total_commits"], int)
        assert data["total_commits"] >= 1
        assert isinstance(data["ai_commits"], int)
        assert isinstance(data["human_commits"], int)
        assert isinstance(data["edited_commits"], int)
        assert isinstance(data["spec_refs"], list)
        assert isinstance(data["task_refs"], list)
        assert isinstance(data["agents"], list)
        assert isinstance(data["pipeline_status"], dict)
        assert isinstance(data["description_md"], str)
        assert "## Summary" in data["description_md"]

    def test_no_commits_json(
        self, runner: CliRunner, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When no commits ahead of base, should error."""
        subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"],
            capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.name", "Test"],
            capture_output=True, check=True,
        )
        (tmp_path / "f.txt").write_text("x\n")
        subprocess.run(["git", "-C", str(tmp_path), "add", "."], capture_output=True, check=True)
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-m", "init"],
            capture_output=True, check=True,
        )

        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["pr", "--json"], catch_exceptions=False)
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["status"] == "error"

    def test_dry_run_text_output(
        self, runner: CliRunner, repo_with_commits: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(repo_with_commits)
        result = runner.invoke(cli, ["pr", "--dry-run"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "## Summary" in result.output
        assert "## Commits" in result.output
