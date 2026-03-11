"""Tests for _baseline_findings_changed() in pipeline stages."""
from __future__ import annotations

import json

from dev_stack.pipeline.stages import _baseline_findings_changed


def test_identical_results_returns_false() -> None:
    """Identical results sections → no change."""
    baseline = json.dumps({
        "generated_at": "2025-01-01T00:00:00Z",
        "version": "1.0",
        "results": {"file.py": [{"type": "Secret", "line": 10}]},
    })
    updated = json.dumps({
        "generated_at": "2025-01-02T00:00:00Z",
        "version": "1.0",
        "results": {"file.py": [{"type": "Secret", "line": 10}]},
    })
    assert _baseline_findings_changed(baseline, updated) is False


def test_differing_results_returns_true() -> None:
    """Different results sections → changed."""
    baseline = json.dumps({
        "generated_at": "2025-01-01T00:00:00Z",
        "results": {"file.py": [{"type": "Secret", "line": 10}]},
    })
    updated = json.dumps({
        "generated_at": "2025-01-02T00:00:00Z",
        "results": {"file.py": [{"type": "Secret", "line": 10}, {"type": "Secret", "line": 20}]},
    })
    assert _baseline_findings_changed(baseline, updated) is True


def test_invalid_json_returns_true() -> None:
    """Invalid JSON → treat as changed (conservative)."""
    assert _baseline_findings_changed("not json", "{}") is True
    assert _baseline_findings_changed("{}", "not json") is True
    assert _baseline_findings_changed("not json", "also not json") is True


def test_empty_results_both_sides() -> None:
    """Both have empty results → no change."""
    baseline = json.dumps({"generated_at": "old", "results": {}})
    updated = json.dumps({"generated_at": "new", "results": {}})
    assert _baseline_findings_changed(baseline, updated) is False


def test_ignores_non_results_keys() -> None:
    """Changes in version, plugins_used, filters_used are ignored."""
    baseline = json.dumps({
        "generated_at": "old",
        "version": "1.0",
        "plugins_used": [{"name": "HexHighEntropyString"}],
        "filters_used": [{"name": "AllowListFilter"}],
        "results": {},
    })
    updated = json.dumps({
        "generated_at": "new",
        "version": "2.0",
        "plugins_used": [{"name": "HexHighEntropyString"}, {"name": "KeywordDetector"}],
        "filters_used": [],
        "results": {},
    })
    assert _baseline_findings_changed(baseline, updated) is False
