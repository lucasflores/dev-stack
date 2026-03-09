"""Unit tests for TrailerPresenceRule (UC2) and TrailerPathRule (UC3).

Validates:
- Agent commits require all five trailers (UC2)
- Manual commits skip trailer validation (UC2)
- Valid trailer paths pass (UC3)
- Non-existent trailer paths produce violations (UC3)
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from dev_stack.rules.trailers import TrailerPathRule, TrailerPresenceRule


class FakeMessage:
    def __init__(self, title: str, body_lines: list[str] | None = None) -> None:
        self.title = title
        self.body = body_lines or []


class FakeCommit:
    def __init__(self, title: str, body_lines: list[str] | None = None) -> None:
        self.message = FakeMessage(title, body_lines)


# ---------------------------------------------------------------------------
# TrailerPresenceRule (UC2) tests
# ---------------------------------------------------------------------------


@pytest.fixture
def presence_rule() -> TrailerPresenceRule:
    return TrailerPresenceRule()


FULL_TRAILERS = [
    "",
    "Spec-Ref: specs/004-vcs-best-practices/spec.md",
    "Task-Ref: specs/004-vcs-best-practices/tasks.md",
    "Agent: claude-sonnet-4-20250514",
    "Pipeline: lint=pass,typecheck=pass,test=pass",
    "Edited: false",
]


def test_agent_commit_with_all_trailers_passes(presence_rule: TrailerPresenceRule) -> None:
    commit = FakeCommit("feat: add feature", FULL_TRAILERS)
    violations = presence_rule.validate(commit)
    assert violations == []


def test_manual_commit_without_agent_trailer_skipped(presence_rule: TrailerPresenceRule) -> None:
    """Manual commits (no Agent trailer) should not be checked."""
    commit = FakeCommit("fix: bug fix", ["", "Some description"])
    violations = presence_rule.validate(commit)
    assert violations == []


def test_agent_commit_missing_spec_ref(presence_rule: TrailerPresenceRule) -> None:
    body = [
        "",
        "Task-Ref: specs/004/tasks.md",
        "Agent: claude-sonnet-4-20250514",
        "Pipeline: lint=pass",
        "Edited: false",
    ]
    commit = FakeCommit("feat: thing", body)
    violations = presence_rule.validate(commit)
    assert len(violations) == 1
    assert "Spec-Ref" in violations[0].message


def test_agent_commit_missing_multiple_trailers(presence_rule: TrailerPresenceRule) -> None:
    body = [
        "",
        "Agent: claude-sonnet-4-20250514",
    ]
    commit = FakeCommit("feat: thing", body)
    violations = presence_rule.validate(commit)
    # Missing: Spec-Ref, Task-Ref, Pipeline, Edited
    assert len(violations) == 4


def test_agent_commit_with_no_body_but_agent_in_trailers(
    presence_rule: TrailerPresenceRule,
) -> None:
    """Edge case: Agent trailer only, everything else missing."""
    body = ["Agent: copilot"]
    commit = FakeCommit("feat: thing", body)
    violations = presence_rule.validate(commit)
    # Missing: Spec-Ref, Task-Ref, Pipeline, Edited
    assert len(violations) == 4


def test_empty_body_no_violations(presence_rule: TrailerPresenceRule) -> None:
    commit = FakeCommit("feat: thing", [])
    violations = presence_rule.validate(commit)
    assert violations == []


def test_none_body_no_violations(presence_rule: TrailerPresenceRule) -> None:
    commit = FakeCommit("feat: thing", None)
    violations = presence_rule.validate(commit)
    assert violations == []


# ---------------------------------------------------------------------------
# TrailerPathRule (UC3) tests
# ---------------------------------------------------------------------------


@pytest.fixture
def path_rule() -> TrailerPathRule:
    return TrailerPathRule()


def test_valid_paths_produce_no_violations(path_rule: TrailerPathRule, tmp_path: Path) -> None:
    # Create referenced files
    spec_dir = tmp_path / "specs" / "004"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text("# Spec")
    (spec_dir / "tasks.md").write_text("# Tasks")

    body = [
        "",
        "Spec-Ref: specs/004/spec.md",
        "Task-Ref: specs/004/tasks.md",
        "Agent: claude-sonnet-4-20250514",
        "Pipeline: lint=pass",
        "Edited: false",
    ]
    commit = FakeCommit("feat: add", body)

    with patch("dev_stack.rules.trailers._get_repo_root", return_value=tmp_path):
        violations = path_rule.validate(commit)
    assert violations == []


def test_nonexistent_spec_ref_produces_violation(
    path_rule: TrailerPathRule, tmp_path: Path
) -> None:
    body = [
        "",
        "Spec-Ref: specs/nonexistent/spec.md",
        "Agent: claude-sonnet-4-20250514",
        "Pipeline: lint=pass",
        "Edited: false",
    ]
    commit = FakeCommit("feat: add", body)

    with patch("dev_stack.rules.trailers._get_repo_root", return_value=tmp_path):
        violations = path_rule.validate(commit)
    assert len(violations) == 1
    assert "Spec-Ref" in violations[0].message
    assert violations[0].rule_id == "UC3"


def test_nonexistent_task_ref_produces_violation(
    path_rule: TrailerPathRule, tmp_path: Path
) -> None:
    body = [
        "",
        "Task-Ref: specs/missing/tasks.md",
        "Agent: claude-sonnet-4-20250514",
        "Pipeline: lint=pass",
        "Edited: false",
    ]
    commit = FakeCommit("feat: add", body)

    with patch("dev_stack.rules.trailers._get_repo_root", return_value=tmp_path):
        violations = path_rule.validate(commit)
    assert len(violations) == 1
    assert "Task-Ref" in violations[0].message


def test_no_path_trailers_skipped(path_rule: TrailerPathRule, tmp_path: Path) -> None:
    """When no Spec-Ref or Task-Ref exist, nothing to validate."""
    body = [
        "",
        "Agent: claude-sonnet-4-20250514",
        "Pipeline: lint=pass",
        "Edited: false",
    ]
    commit = FakeCommit("feat: add", body)

    with patch("dev_stack.rules.trailers._get_repo_root", return_value=tmp_path):
        violations = path_rule.validate(commit)
    assert violations == []


def test_no_repo_root_skips_validation(path_rule: TrailerPathRule) -> None:
    """If repo root can't be detected, skip path validation."""
    body = [
        "",
        "Spec-Ref: specs/004/spec.md",
        "Agent: claude-sonnet-4-20250514",
        "Pipeline: lint=pass",
        "Edited: false",
    ]
    commit = FakeCommit("feat: add", body)

    with patch("dev_stack.rules.trailers._get_repo_root", return_value=None):
        violations = path_rule.validate(commit)
    assert violations == []
