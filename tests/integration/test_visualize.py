"""Integration tests for the visualize CLI command."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dev_stack.cli.main import cli
from dev_stack.visualization.understand_runner import KNOWLEDGE_GRAPH_FILE, UNDERSTAND_OUTPUT_DIR


def _write_graph(repo_root: Path) -> None:
    graph_dir = repo_root / UNDERSTAND_OUTPUT_DIR
    graph_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "project": {
            "name": "test-repo",
            "analyzedAt": "2026-04-22T12:00:00Z",
            "gitCommitHash": "abc123",
        },
        "nodes": [
            {"filePath": "src/dev_stack/cli/visualize_cmd.py"},
            {"filePath": "tests/integration/test_visualize.py"},
        ],
    }
    (graph_dir / KNOWLEDGE_GRAPH_FILE).write_text(json.dumps(payload), encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestVisualizeCommand:
    """Integration tests for `dev-stack visualize`."""

    def test_successful_validation(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Committed graph artifacts validate successfully."""

        monkeypatch.chdir(tmp_path)
        _write_graph(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["--json", "visualize"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["status"] == "pass"
        assert payload["blocked"] is False
        assert payload["output_dir"] == str(UNDERSTAND_OUTPUT_DIR)
        assert payload["project"]["name"] == "test-repo"

    def test_json_output(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """JSON output supports incremental skip path."""

        monkeypatch.chdir(tmp_path)
        _write_graph(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["--json", "visualize", "--incremental"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["status"] == "success"
        assert payload["skipped"] is True
        assert "No changed paths detected" in payload["reason"]

    def test_no_readme_flag(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """--no-readme remains accepted for compatibility."""

        monkeypatch.chdir(tmp_path)
        _write_graph(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["--json", "visualize", "--no-readme"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["blocked"] is False

    def test_cli_missing_exits_code_4(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Missing graph artifact produces exit code 1 with remediation."""

        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["--json", "visualize"])

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["status"] == "error"
        assert "missing" in payload["message"].lower()

    def test_codeboarding_failure_exits_code_1(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Graph-impacting changes without synced graph updates block validation."""

        monkeypatch.chdir(tmp_path)
        _write_graph(tmp_path)

        runner = CliRunner()
        with patch(
            "dev_stack.visualization.graph_policy.collect_changed_paths",
            return_value=["src/dev_stack/cli/visualize_cmd.py"],
        ):
            result = runner.invoke(cli, ["--json", "visualize"])

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["status"] == "error"
        assert payload["blocked"] is True
        assert payload["freshness_state"] in {"STALE", "INDETERMINATE"}

    def test_incremental_no_changes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unsupported plugin value emits remediation warning."""

        monkeypatch.chdir(tmp_path)
        _write_graph(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["--json", "visualize", "--plugin", "unknown-plugin"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["status"] == "pass"
        assert payload["warnings"]
        assert "Unsupported plugin workflow" in payload["warnings"][0]

    def test_indeterminate_detection_blocks_merge_scope(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing node coverage with source changes fails closed as indeterminate."""

        monkeypatch.chdir(tmp_path)
        graph_dir = tmp_path / UNDERSTAND_OUTPUT_DIR
        graph_dir.mkdir(parents=True, exist_ok=True)
        (graph_dir / KNOWLEDGE_GRAPH_FILE).write_text(
            json.dumps(
                {
                    "project": {
                        "name": "test-repo",
                        "analyzedAt": "2026-04-22T12:00:00Z",
                        "gitCommitHash": "abc123",
                    },
                    "nodes": [],
                }
            ),
            encoding="utf-8",
        )

        runner = CliRunner()
        with patch(
            "dev_stack.visualization.graph_policy.collect_changed_paths",
            return_value=["src/dev_stack/new_file.py"],
        ):
            result = runner.invoke(cli, ["--json", "visualize"])

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["status"] == "error"
        assert payload["freshness_state"] == "INDETERMINATE"
