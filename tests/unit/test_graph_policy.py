"""Unit tests for graph_policy."""
from __future__ import annotations

import json
from pathlib import Path

from dev_stack.visualization.graph_policy import (
    GraphFreshnessState,
    detect_legacy_reference_violations,
    evaluate_graph_impact,
    evaluate_storage_policy,
    has_graph_updates,
    validate_graph_freshness,
)


def test_evaluate_graph_impact_prefers_diff_overlay() -> None:
    result = evaluate_graph_impact(
        changed_paths=["src/dev_stack/cli/visualize_cmd.py"],
        graph_node_file_paths={"src/dev_stack/cli/visualize_cmd.py"},
        diff_overlay_present=True,
    )

    assert result.detection_mode == "diff_overlay"
    assert result.is_graph_impacting is True


def test_evaluate_graph_impact_path_intersection() -> None:
    result = evaluate_graph_impact(
        changed_paths=["src/dev_stack/cli/visualize_cmd.py", "README.md"],
        graph_node_file_paths={"src/dev_stack/cli/visualize_cmd.py"},
        diff_overlay_present=False,
    )

    assert result.detection_mode == "graph_path_intersection"
    assert result.matched_paths == ["src/dev_stack/cli/visualize_cmd.py"]
    assert result.is_graph_impacting is True


def test_evaluate_graph_impact_indeterminate_without_coverage() -> None:
    result = evaluate_graph_impact(
        changed_paths=["src/new_module.py"],
        graph_node_file_paths=set(),
        diff_overlay_present=False,
    )

    assert result.detection_mode == "indeterminate"
    assert result.is_graph_impacting is True


def test_has_graph_updates_excludes_scratch_artifacts() -> None:
    assert has_graph_updates([".understand-anything/knowledge-graph.json"]) is True
    assert has_graph_updates([".understand-anything/intermediate/run-1.json"]) is False
    assert has_graph_updates([".understand-anything/diff-overlay.json"]) is False


def test_evaluate_storage_policy_requires_lfs_for_large_json(tmp_path: Path) -> None:
    graph_dir = tmp_path / ".understand-anything"
    graph_dir.mkdir(parents=True, exist_ok=True)

    large_path = graph_dir / "knowledge-graph.json"
    large_path.write_text(json.dumps({"data": "x" * 1024}), encoding="utf-8")

    # Force low threshold so fixture file is considered oversized.
    policy = evaluate_storage_policy(tmp_path, max_inline_json_bytes=100)

    assert policy.requires_lfs is True
    assert policy.gitattributes_has_lfs_rule is False
    assert policy.violations


def test_validate_graph_freshness_blocks_stale_changes() -> None:
    impact = evaluate_graph_impact(
        changed_paths=["src/dev_stack/cli/visualize_cmd.py"],
        graph_node_file_paths={"src/dev_stack/cli/visualize_cmd.py"},
        diff_overlay_present=False,
    )
    storage = evaluate_storage_policy(Path("."), max_inline_json_bytes=10**9)

    outcome = validate_graph_freshness(
        enforcement_scope="pre_commit",
        impact_evaluation=impact,
        storage_policy=storage,
        graph_updated_in_change_set=False,
        has_knowledge_graph=True,
    )

    assert outcome.status == "fail"
    assert outcome.blocked is True
    assert outcome.freshness_state == GraphFreshnessState.STALE


def test_validate_graph_freshness_passes_when_graph_is_synced() -> None:
    impact = evaluate_graph_impact(
        changed_paths=["src/dev_stack/cli/visualize_cmd.py", ".understand-anything/knowledge-graph.json"],
        graph_node_file_paths={"src/dev_stack/cli/visualize_cmd.py"},
        diff_overlay_present=False,
    )
    storage = evaluate_storage_policy(Path("."), max_inline_json_bytes=10**9)

    outcome = validate_graph_freshness(
        enforcement_scope="pre_commit",
        impact_evaluation=impact,
        storage_policy=storage,
        graph_updated_in_change_set=True,
        has_knowledge_graph=True,
    )

    assert outcome.status == "pass"
    assert outcome.blocked is False
    assert outcome.freshness_state == GraphFreshnessState.CURRENT


def test_detect_legacy_reference_violations(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Legacy CodeBoarding notes", encoding="utf-8")

    violations = detect_legacy_reference_violations(tmp_path)

    assert violations
    assert violations[0].startswith("README.md")
