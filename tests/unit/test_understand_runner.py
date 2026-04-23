"""Unit tests for understand_runner."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from dev_stack.errors import VisualizationError
from dev_stack.visualization.understand_runner import (
    KNOWLEDGE_GRAPH_FILE,
    UNDERSTAND_OUTPUT_DIR,
    extract_graph_metadata,
    load_knowledge_graph,
    verify_bootstrap,
)


def _write_graph(repo_root: Path) -> None:
    graph_dir = repo_root / UNDERSTAND_OUTPUT_DIR
    graph_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "project": {
            "name": "demo",
            "analyzedAt": "2026-04-22T00:00:00Z",
            "gitCommitHash": "abc123",
        },
        "nodes": [
            {"filePath": "src/dev_stack/cli/visualize_cmd.py"},
            {"filePath": "tests/integration/test_visualize.py"},
        ],
    }
    (graph_dir / KNOWLEDGE_GRAPH_FILE).write_text(json.dumps(payload), encoding="utf-8")


class TestVerifyBootstrap:
    def test_fail_when_missing_graph_file(self, tmp_path: Path) -> None:
        result = verify_bootstrap(tmp_path)
        assert result.status == "fail"
        assert result.has_knowledge_graph is False
        assert KNOWLEDGE_GRAPH_FILE in result.missing_files

    def test_pass_when_required_file_exists(self, tmp_path: Path) -> None:
        _write_graph(tmp_path)

        result = verify_bootstrap(tmp_path)

        assert result.status == "pass"
        assert result.has_knowledge_graph is True
        assert result.project_name == "demo"
        assert result.analyzed_at == "2026-04-22T00:00:00Z"
        assert result.git_commit_hash == "abc123"


class TestLoadKnowledgeGraph:
    def test_raises_for_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(VisualizationError, match="Required graph artifact"):
            load_knowledge_graph(tmp_path)

    def test_raises_for_invalid_json(self, tmp_path: Path) -> None:
        graph_dir = tmp_path / UNDERSTAND_OUTPUT_DIR
        graph_dir.mkdir(parents=True, exist_ok=True)
        (graph_dir / KNOWLEDGE_GRAPH_FILE).write_text("{not-json", encoding="utf-8")

        with pytest.raises(VisualizationError, match="Failed to parse"):
            load_knowledge_graph(tmp_path)


class TestExtractGraphMetadata:
    def test_extracts_project_and_node_paths(self) -> None:
        payload = {
            "project": {
                "name": "repo",
                "analyzedAt": "2026-04-22T00:00:00Z",
                "gitCommitHash": "deadbeef",
            },
            "nodes": [
                {"filePath": "src/a.py"},
                {"path": "src/b.py"},
                {"reference_file": "tests/test_a.py"},
            ],
        }

        metadata = extract_graph_metadata(payload)

        assert metadata.project_name == "repo"
        assert metadata.analyzed_at == "2026-04-22T00:00:00Z"
        assert metadata.git_commit_hash == "deadbeef"
        assert metadata.node_file_paths == {"src/a.py", "src/b.py", "tests/test_a.py"}
