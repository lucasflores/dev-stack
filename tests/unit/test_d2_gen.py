"""Tests for D2 generator output."""
from __future__ import annotations

import json
from pathlib import Path

from dev_stack.visualization.d2_gen import D2Generator


def _sample_schema() -> dict:
    return {
        "nodes": [
            {
                "id": "ep.cli.start",
                "type": "entry_point",
                "name": "CLI",
                "description": "User entry point",
                "files": [{"file": "src/dev_stack/cli/main.py", "lines": [1, 40]}],
            },
            {
                "id": "fb.visualization",
                "type": "feature_block",
                "name": "Visualization",
                "description": "Generates diagrams",
                "files": [{"file": "src/dev_stack/visualization/d2_gen.py", "lines": [1, 120]}],
            },
            {
                "id": "end.done",
                "type": "end",
                "name": "Docs",
                "description": "Diagram shipped",
                "files": [{"file": "docs/diagrams/overview.svg", "lines": [1, 1]}],
            },
        ],
        "flows": [
            {"from": "ep.cli.start", "to": "fb.visualization", "description": "Invokes"},
            {"from": "fb.visualization", "to": "end.done", "description": "Outputs"},
        ],
    }


def test_render_overview_includes_styles(tmp_path: Path) -> None:
    schema = _sample_schema()
    generator = D2Generator(tmp_path)
    highlight = {"src/dev_stack/cli/main.py"}

    d2_text = generator.render_overview(schema, highlight_paths=highlight)

    assert "diagram {" in d2_text
    assert "ep_cli_start" in d2_text  # sanitized id
    assert "[updated]" in d2_text  # badge appended to entry point label
    assert "class: entry_node" in d2_text
    assert "fb_visualization" in d2_text
    assert "label: \"Visualization" in d2_text
    assert "ep_cli_start -> fb_visualization" in d2_text
    assert "class: flow_link" in d2_text


def test_render_json_normalizes_nodes(tmp_path: Path) -> None:
    schema = _sample_schema()
    generator = D2Generator(tmp_path)
    output_path = tmp_path / "overview.json"

    normalized = generator.render_json(schema, output_path=output_path, highlight_paths=set())

    assert output_path.exists()
    data = json.loads(output_path.read_text())
    assert data == normalized
    assert "src/dev_stack/cli/main.py" in normalized["nodes"]
    node = normalized["nodes"]["src/dev_stack/cli/main.py"]
    assert node["status"] == "unchanged"
    assert node["type"] == "entry_point"
    assert isinstance(node["files"], list)
