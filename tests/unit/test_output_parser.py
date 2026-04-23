"""Unit tests for output_parser."""
from __future__ import annotations

import json
import inspect
from pathlib import Path

import pytest

from dev_stack.cli import visualize_cmd
from dev_stack.errors import CodeBoardingError
from dev_stack.visualization.output_parser import (
    AnalysisIndex,
    ParsedComponent,
    compute_target_folder,
    derive_markdown_filename,
    extract_mermaid,
    parse_analysis_index,
    parse_components,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_ANALYSIS: dict = {
    "metadata": {
        "generated_at": "2026-03-04T12:00:00Z",
        "repo_name": "test-repo",
        "depth_level": 2,
        "file_coverage_summary": {"total_files": 10, "analyzed": 8},
    },
    "description": "A test repo",
    "components": [
        {
            "name": "Agent Core",
            "description": "Core agent logic",
            "key_entities": [
                {"qualified_name": "agent.Agent", "reference_file": "agent.py"},
            ],
            "assigned_files": ["agent.py", "agent_utils.py"],
            "source_cluster_ids": [1],
            "component_id": "abcdef0123456789",
            "can_expand": True,
            "components": [
                {
                    "name": "Planner",
                    "description": "Planning logic",
                    "key_entities": [],
                    "assigned_files": ["planner.py"],
                    "source_cluster_ids": [],
                    "component_id": "1234567890abcdef",
                    "can_expand": False,
                    "components": [],
                    "components_relations": [],
                }
            ],
            "components_relations": [],
        },
        {
            "name": "CLI Interface",
            "description": "Command-line interface",
            "key_entities": [],
            "assigned_files": ["cli/main.py", "cli/utils.py"],
            "source_cluster_ids": [2],
            "component_id": "fedcba9876543210",
            "can_expand": False,
            "components": [],
            "components_relations": [],
        },
    ],
    "components_relations": [
        {
            "relation": "uses",
            "src_name": "CLI Interface",
            "dst_name": "Agent Core",
            "src_id": "fedcba9876543210",
            "dst_id": "abcdef0123456789",
        }
    ],
}


SAMPLE_MERMAID_MD = """\
# Agent Core

```mermaid
graph LR
  A[Agent] --> B[Planner]
  B --> C[Executor]
```

## Details

Some description here.
"""

SAMPLE_NO_MERMAID_MD = """\
# Agent Core

No diagrams here, just text.
"""


# ---------------------------------------------------------------------------
# parse_analysis_index
# ---------------------------------------------------------------------------


class TestParseAnalysisIndex:
    def test_valid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "analysis.json"
        path.write_text(json.dumps(VALID_ANALYSIS), encoding="utf-8")

        index = parse_analysis_index(path)

        assert isinstance(index, AnalysisIndex)
        assert index.metadata.repo_name == "test-repo"
        assert index.metadata.depth_level == 2
        assert len(index.components) == 2
        assert index.components[0].name == "Agent Core"
        assert index.components[0].can_expand is True
        assert len(index.components[0].components) == 1
        assert len(index.components_relations) == 1
        assert index.components_relations[0].relation == "uses"

    def test_missing_file(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.json"
        with pytest.raises(CodeBoardingError, match="not found"):
            parse_analysis_index(path)

    def test_malformed_json(self, tmp_path: Path) -> None:
        path = tmp_path / "analysis.json"
        path.write_text("{invalid json!!!", encoding="utf-8")
        with pytest.raises(CodeBoardingError, match="Failed to parse"):
            parse_analysis_index(path)

    def test_non_object_json(self, tmp_path: Path) -> None:
        path = tmp_path / "analysis.json"
        path.write_text('"just a string"', encoding="utf-8")
        with pytest.raises(CodeBoardingError, match="Expected JSON object"):
            parse_analysis_index(path)


# ---------------------------------------------------------------------------
# extract_mermaid
# ---------------------------------------------------------------------------


class TestExtractMermaid:
    def test_extracts_first_mermaid_block(self, tmp_path: Path) -> None:
        md = tmp_path / "component.md"
        md.write_text(SAMPLE_MERMAID_MD, encoding="utf-8")

        result = extract_mermaid(md)

        assert result is not None
        assert "graph LR" in result
        assert "A[Agent]" in result

    def test_returns_none_for_no_mermaid(self, tmp_path: Path) -> None:
        md = tmp_path / "component.md"
        md.write_text(SAMPLE_NO_MERMAID_MD, encoding="utf-8")

        assert extract_mermaid(md) is None

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        assert extract_mermaid(tmp_path / "nonexistent.md") is None


# ---------------------------------------------------------------------------
# derive_markdown_filename
# ---------------------------------------------------------------------------


class TestDeriveMarkdownFilename:
    def test_spaces_to_underscores(self) -> None:
        assert derive_markdown_filename("LLM Agent Core") == "LLM_Agent_Core.md"

    def test_special_chars_to_underscores(self) -> None:
        assert (
            derive_markdown_filename("Application Orchestrator & Repository Manager")
            == "Application_Orchestrator_Repository_Manager.md"
        )

    def test_simple_name(self) -> None:
        assert derive_markdown_filename("CLI") == "CLI.md"

    def test_numeric_name(self) -> None:
        assert derive_markdown_filename("Component123") == "Component123.md"


# ---------------------------------------------------------------------------
# compute_target_folder
# ---------------------------------------------------------------------------


class TestComputeTargetFolder:
    def test_common_directory(self) -> None:
        assert compute_target_folder(["agents/agent.py", "agents/constants.py"]) == "agents"

    def test_nested_common_directory(self) -> None:
        assert compute_target_folder(["src/core/a.py", "src/core/b.py"]) == "src/core"

    def test_no_common_prefix(self) -> None:
        assert compute_target_folder(["agents/a.py", "cli/b.py"]) is None

    def test_root_level_files(self) -> None:
        assert compute_target_folder(["main.py"]) is None

    def test_empty_list(self) -> None:
        assert compute_target_folder([]) is None

    def test_single_file_in_subdir(self) -> None:
        assert compute_target_folder(["src/utils/helper.py"]) == "src/utils"


# ---------------------------------------------------------------------------
# parse_components (end-to-end orchestration)
# ---------------------------------------------------------------------------


class TestParseComponents:
    def test_full_orchestration(self, tmp_path: Path) -> None:
        # Set up .codeboarding/ directory
        cb_dir = tmp_path / ".codeboarding"
        cb_dir.mkdir()

        # Write analysis.json
        (cb_dir / "analysis.json").write_text(json.dumps(VALID_ANALYSIS), encoding="utf-8")

        # Write component markdown files
        (cb_dir / "Agent_Core.md").write_text(SAMPLE_MERMAID_MD, encoding="utf-8")
        (cb_dir / "CLI_Interface.md").write_text(SAMPLE_NO_MERMAID_MD, encoding="utf-8")
        # Sub-component md
        (cb_dir / "Planner.md").write_text(
            "```mermaid\ngraph LR\n  P[Plan]\n```\n", encoding="utf-8"
        )

        components = parse_components(cb_dir)

        assert len(components) == 2
        assert components[0].name == "Agent Core"
        assert components[0].mermaid is not None
        assert "graph LR" in components[0].mermaid
        assert len(components[0].sub_components) == 1
        assert components[0].sub_components[0].name == "Planner"

        # target_folder should be computed from assigned_files
        # agent.py + agent_utils.py are root-level → None
        assert components[0].target_folder is None
        # cli/main.py + cli/utils.py → "cli"
        assert components[1].target_folder == "cli"

        # CLI Interface has no mermaid
        assert components[1].name == "CLI Interface"
        assert components[1].mermaid is None

    def test_missing_md_logs_warning(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        cb_dir = tmp_path / ".codeboarding"
        cb_dir.mkdir()

        minimal = {
            "metadata": {"generated_at": "", "repo_name": "x", "depth_level": 1},
            "description": "",
            "components": [
                {
                    "name": "MissingComponent",
                    "description": "",
                    "key_entities": [],
                    "assigned_files": [],
                    "component_id": "0000000000000000",
                    "can_expand": False,
                    "components": [],
                    "components_relations": [],
                }
            ],
            "components_relations": [],
        }
        (cb_dir / "analysis.json").write_text(json.dumps(minimal), encoding="utf-8")

        with caplog.at_level("WARNING"):
            components = parse_components(cb_dir)

        assert len(components) == 1
        assert components[0].mermaid is None
        assert "Missing or empty Mermaid" in caplog.text


def test_visualize_cli_no_longer_imports_parser_or_readme_injector() -> None:
    source = inspect.getsource(visualize_cmd)
    assert "parse_components" not in source
    assert "inject_root_diagram" not in source
    assert "inject_component_diagrams" not in source
