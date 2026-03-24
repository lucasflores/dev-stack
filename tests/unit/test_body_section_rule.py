"""Tests for BodySectionRule (UC5).

Validates:
- Agent commit with all 4 sections → PASS
- Agent commit with no body sections → FAIL listing all 4
- Agent commit with partial sections → FAIL listing missing
- Human commit with no body sections → PASS (not enforced)
- Agent commit with h3 instead of h2 → FAIL
"""
from __future__ import annotations

import pytest

from dev_stack.rules.body_sections import BodySectionRule


class FakeMessage:
    def __init__(self, title: str, body_lines: list[str] | None = None) -> None:
        self.title = title
        self.body = body_lines or []


class FakeCommit:
    def __init__(self, title: str, body_lines: list[str] | None = None) -> None:
        self.message = FakeMessage(title, body_lines)


@pytest.fixture
def rule() -> BodySectionRule:
    return BodySectionRule()


AGENT_TRAILERS = [
    "",
    "Spec-Ref: specs/012/spec.md",
    "Task-Ref: specs/012/tasks.md",
    "Agent: claude-sonnet-4-20250514",
    "Pipeline: lint=pass,test=pass",
    "Edited: false",
]

ALL_SECTIONS = [
    "",
    "## Intent",
    "Why this change exists.",
    "",
    "## Reasoning",
    "Critical decisions and trade-offs.",
    "",
    "## Scope",
    "Components and files touched.",
    "",
    "## Narrative",
    "Summary of the change.",
    "",
]


def test_agent_commit_with_all_sections_passes(rule: BodySectionRule) -> None:
    """T020: Agent commit with all 4 body sections → no violations."""
    commit = FakeCommit("feat: add feature", ALL_SECTIONS + AGENT_TRAILERS)
    violations = rule.validate(commit)
    assert violations == []


def test_agent_commit_no_sections_fails(rule: BodySectionRule) -> None:
    """T021: Agent commit with no body sections → fail listing all 4."""
    commit = FakeCommit("feat: add feature", AGENT_TRAILERS)
    violations = rule.validate(commit)
    assert len(violations) == 1
    msg = violations[0].message
    assert "## Intent" in msg
    assert "## Reasoning" in msg
    assert "## Scope" in msg
    assert "## Narrative" in msg


def test_agent_commit_partial_sections_fails(rule: BodySectionRule) -> None:
    """T022: Agent commit with Intent + Scope only → fail listing Reasoning, Narrative."""
    body = [
        "",
        "## Intent",
        "Why.",
        "",
        "## Scope",
        "What.",
        "",
    ] + AGENT_TRAILERS
    commit = FakeCommit("feat: add feature", body)
    violations = rule.validate(commit)
    assert len(violations) == 1
    msg = violations[0].message
    # The "missing" portion lists only what's absent
    missing_part = msg.split(".")[0]  # before the first period
    assert "## Reasoning" in missing_part
    assert "## Narrative" in missing_part
    assert "## Intent" not in missing_part
    assert "## Scope" not in missing_part


def test_human_commit_no_sections_passes(rule: BodySectionRule) -> None:
    """T023: Human commit (no Agent: trailer) with no body sections → PASS."""
    commit = FakeCommit("fix: typo", ["Some body text."])
    violations = rule.validate(commit)
    assert violations == []


def test_agent_commit_h3_instead_of_h2_fails(rule: BodySectionRule) -> None:
    """T024: Agent commit with ### Intent (h3) → FAIL (must be ## not ###)."""
    body = [
        "",
        "### Intent",
        "Why.",
        "",
        "### Reasoning",
        "Decisions.",
        "",
        "### Scope",
        "Files.",
        "",
        "### Narrative",
        "Summary.",
        "",
    ] + AGENT_TRAILERS
    commit = FakeCommit("feat: add feature", body)
    violations = rule.validate(commit)
    assert len(violations) == 1
    msg = violations[0].message
    assert "## Intent" in msg
