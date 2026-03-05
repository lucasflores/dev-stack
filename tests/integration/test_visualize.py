"""Integration tests for the visualize CLI command."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from dev_stack.cli.main import cli
from dev_stack.visualization.codeboarding_runner import RunResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_codeboarding_output(repo_root: Path) -> None:
    """Create a fake .codeboarding/ directory with valid output files."""

    cb_dir = repo_root / ".codeboarding"
    cb_dir.mkdir(parents=True, exist_ok=True)

    analysis = {
        "metadata": {
            "generated_at": "2026-03-04T12:00:00Z",
            "repo_name": "test-repo",
            "depth_level": 2,
            "file_coverage_summary": {},
        },
        "description": "Test repository",
        "components": [
            {
                "name": "Core",
                "description": "Core logic",
                "key_entities": [],
                "assigned_files": ["src/core/main.py", "src/core/utils.py"],
                "source_cluster_ids": [],
                "component_id": "abcdef0123456789",
                "can_expand": False,
                "components": [],
                "components_relations": [],
            },
            {
                "name": "CLI",
                "description": "Command-line interface",
                "key_entities": [],
                "assigned_files": ["cli/app.py"],
                "source_cluster_ids": [],
                "component_id": "1234567890abcdef",
                "can_expand": False,
                "components": [],
                "components_relations": [],
            },
        ],
        "components_relations": [],
    }
    (cb_dir / "analysis.json").write_text(json.dumps(analysis), encoding="utf-8")

    overview_md = "# Overview\n\n```mermaid\ngraph LR\n  Core --> CLI\n```\n\n## Details\n"
    (cb_dir / "overview.md").write_text(overview_md, encoding="utf-8")

    core_md = "# Core\n\n```mermaid\ngraph LR\n  Main --> Utils\n```\n"
    (cb_dir / "Core.md").write_text(core_md, encoding="utf-8")

    # CLI component has no Mermaid
    (cb_dir / "CLI.md").write_text("# CLI\n\nNo diagram.\n", encoding="utf-8")


def _mock_successful_run(repo_root: Path, **kwargs) -> RunResult:
    """Mock run that creates .codeboarding/ output and returns success."""
    _setup_codeboarding_output(repo_root)
    return RunResult(success=True, stdout="Done", stderr="", return_code=0)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestVisualizeCommand:
    """Integration tests for `dev-stack visualize`."""

    def test_successful_visualization(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Full happy-path: CodeBoarding runs, output parsed, README injected."""

        monkeypatch.chdir(tmp_path)
        (tmp_path / "README.md").write_text("# Test Project\n", encoding="utf-8")
        (tmp_path / ".dev-stack" / "viz").mkdir(parents=True)
        (tmp_path / ".codeboarding").mkdir()

        runner = CliRunner()
        with (
            patch("dev_stack.cli.visualize_cmd.codeboarding_runner.check_cli_available", return_value=True),
            patch("dev_stack.cli.visualize_cmd.codeboarding_runner.run", side_effect=lambda rr, **kw: _mock_successful_run(rr, **kw)),
            patch("dev_stack.visualization.incremental.ManifestStore.load_manifest"),
            patch("dev_stack.visualization.incremental.ManifestStore.build_manifest"),
            patch("dev_stack.visualization.incremental.ManifestStore.save_manifest"),
        ):
            result = runner.invoke(cli, ["visualize"])

        assert result.exit_code == 0, result.output
        assert "Visualization complete" in result.output

        readme_text = (tmp_path / "README.md").read_text(encoding="utf-8")
        assert "DEV-STACK:BEGIN:architecture" in readme_text
        assert "graph LR" in readme_text
        assert "Core --> CLI" in readme_text

    def test_json_output(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """JSON output matches cli-contract.md schema."""

        monkeypatch.chdir(tmp_path)
        (tmp_path / "README.md").write_text("# Test\n", encoding="utf-8")
        (tmp_path / ".dev-stack" / "viz").mkdir(parents=True)
        (tmp_path / ".codeboarding").mkdir()

        runner = CliRunner()
        with (
            patch("dev_stack.cli.visualize_cmd.codeboarding_runner.check_cli_available", return_value=True),
            patch("dev_stack.cli.visualize_cmd.codeboarding_runner.run", side_effect=lambda rr, **kw: _mock_successful_run(rr, **kw)),
            patch("dev_stack.visualization.incremental.ManifestStore.load_manifest"),
            patch("dev_stack.visualization.incremental.ManifestStore.build_manifest"),
            patch("dev_stack.visualization.incremental.ManifestStore.save_manifest"),
        ):
            result = runner.invoke(cli, ["--json", "visualize"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["status"] == "success"
        assert payload["components_found"] == 2
        assert payload["diagrams_injected"] >= 1
        assert "README.md" in payload["readmes_modified"]
        assert payload["skipped"] is False

    def test_no_readme_flag(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """--no-readme produces .codeboarding/ but no README changes."""

        monkeypatch.chdir(tmp_path)
        (tmp_path / "README.md").write_text("# Untouched\n", encoding="utf-8")
        (tmp_path / ".dev-stack" / "viz").mkdir(parents=True)
        (tmp_path / ".codeboarding").mkdir()

        runner = CliRunner()
        with (
            patch("dev_stack.cli.visualize_cmd.codeboarding_runner.check_cli_available", return_value=True),
            patch("dev_stack.cli.visualize_cmd.codeboarding_runner.run", side_effect=lambda rr, **kw: _mock_successful_run(rr, **kw)),
            patch("dev_stack.visualization.incremental.ManifestStore.load_manifest"),
            patch("dev_stack.visualization.incremental.ManifestStore.build_manifest"),
            patch("dev_stack.visualization.incremental.ManifestStore.save_manifest"),
        ):
            result = runner.invoke(cli, ["--json", "visualize", "--no-readme"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["diagrams_injected"] == 0
        assert payload["readmes_modified"] == []

        # README should be untouched
        assert (tmp_path / "README.md").read_text(encoding="utf-8") == "# Untouched\n"

    def test_cli_missing_exits_code_4(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Missing CodeBoarding CLI produces exit code 4 with guidance."""

        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        with patch("dev_stack.cli.visualize_cmd.codeboarding_runner.check_cli_available", return_value=False):
            result = runner.invoke(cli, ["--json", "visualize"])

        # Exit code 4 (AGENT_UNAVAILABLE)
        assert result.exit_code == 4
        payload = json.loads(result.output)
        assert payload["status"] == "error"
        assert "not found" in payload["message"].lower()

    def test_codeboarding_failure_exits_code_1(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-zero CodeBoarding exit produces exit code 1."""

        monkeypatch.chdir(tmp_path)
        (tmp_path / ".dev-stack" / "viz").mkdir(parents=True)
        (tmp_path / ".codeboarding").mkdir()

        failed_result = RunResult(success=False, stdout="", stderr="API key invalid", return_code=1)
        runner = CliRunner()
        with (
            patch("dev_stack.cli.visualize_cmd.codeboarding_runner.check_cli_available", return_value=True),
            patch("dev_stack.cli.visualize_cmd.codeboarding_runner.run", return_value=failed_result),
        ):
            result = runner.invoke(cli, ["--json", "visualize"])

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["status"] == "error"
        assert "API key invalid" in payload["message"]

    def test_incremental_no_changes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """--incremental with no file changes reports 'up to date'."""

        monkeypatch.chdir(tmp_path)
        (tmp_path / ".dev-stack" / "viz").mkdir(parents=True)

        mock_manifest = MagicMock()
        mock_manifest.files = {"a.py": MagicMock(hash="abc")}

        runner = CliRunner()
        with (
            patch("dev_stack.cli.visualize_cmd.codeboarding_runner.check_cli_available", return_value=True),
            patch("dev_stack.visualization.incremental.ManifestStore.load_manifest", return_value=mock_manifest),
            patch("dev_stack.visualization.incremental.ManifestStore.build_manifest", return_value=mock_manifest),
            patch("dev_stack.visualization.incremental.ManifestStore.changed_paths", return_value=set()),
        ):
            result = runner.invoke(cli, ["--json", "visualize", "--incremental"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["skipped"] is True
        assert payload["reason"] == "No files changed since last run"
